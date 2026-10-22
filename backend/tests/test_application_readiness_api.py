
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.models import Scheme, SchemeVersion
from app.database.session import get_db
from app.main import app


@pytest.fixture
def client_and_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    # This project uses PostgreSQL JSONB types. SQLite may not support every
    # PostgreSQL-specific model type, so create the test schema only if it works.
    Base.metadata.create_all(engine)

    session = TestingSession()
    app.dependency_overrides[get_db] = lambda: session

    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_invalid_scheme_id_returns_422(client_and_session):
    client, _ = client_and_session

    response = client.post(
        "/api/applications/readiness",
        json={
            "scheme_id": "not-a-uuid",
            "submitted_document_types": [],
        },
    )

    assert response.status_code == 422


def test_unknown_scheme_returns_404(client_and_session):
    client, _ = client_and_session

    response = client.post(
        "/api/applications/readiness",
        json={
            "scheme_id": str(uuid4()),
            "submitted_document_types": [],
        },
    )

    assert response.status_code == 404

def test_readiness_uses_latest_approved_version(client_and_session):
    client, session = client_and_session

    scheme = Scheme(
        id=uuid4(),
        slug="test-document-readiness",
        title="Test Document Readiness",
        government_level="central",
        status="published",
    )
    session.add(scheme)
    session.flush()

    session.add_all(
        [
            SchemeVersion(
                id=uuid4(),
                scheme_id=scheme.id,
                version_number=1,
                language="en",
                review_status="approved",
                required_documents=["Identity proof"],
            ),
            SchemeVersion(
                id=uuid4(),
                scheme_id=scheme.id,
                version_number=2,
                language="en",
                review_status="approved",
                required_documents=[
                    "Identity proof",
                    "Income certificate",
                ],
            ),
        ]
    )
    session.commit()

    response = client.post(
        "/api/applications/readiness",
        json={
            "scheme_id": str(scheme.id),
            "submitted_document_types": ["Identity proof"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["scheme_version"] == 2
    assert data["status"] == "NEEDS_ATTENTION"
    assert data["missing_documents"] == ["Income certificate"]


def test_readiness_returns_ready_when_all_types_are_present(
    client_and_session,
):
    client, session = client_and_session

    scheme = Scheme(
        id=uuid4(),
        slug="test-readiness-complete",
        title="Test Complete Readiness",
        government_level="central",
        status="published",
    )
    session.add(scheme)
    session.flush()

    session.add(
        SchemeVersion(
            id=uuid4(),
            scheme_id=scheme.id,
            version_number=1,
            language="en",
            review_status="approved",
            required_documents=["Identity proof"],
        )
    )
    session.commit()

    response = client.post(
        "/api/applications/readiness",
        json={
            "scheme_id": str(scheme.id),
            "submitted_document_types": ["Identity proof"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["missing_documents"] == []
    assert data["authenticity_verified"] is False
