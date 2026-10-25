
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.database.models import Scheme
from app.ingestion.schemas import SchemeIngestionInput
from app.ingestion.service import DuplicateSchemeError, ingest_scheme
from app.main import app
from app.api.auth import get_current_user
from app.database.session import get_db


def make_input(**overrides):
    values = {
        "slug": "test-scheme",
        "title": "Test Scheme",
        "government_level": "central",
        "language": "en",
        "source_url": "https://example.gov.in/scheme",
        "retrieved_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return SchemeIngestionInput(**values)


def test_duplicate_slug_is_rejected():
    db = MagicMock()
    db.scalar.return_value = Scheme(slug="test-scheme", title="Existing")

    with pytest.raises(DuplicateSchemeError):
        ingest_scheme(db, make_input())

    db.add.assert_not_called()


def test_database_error_rolls_back():
    db = MagicMock()
    db.scalar.return_value = None
    db.flush.side_effect = SQLAlchemyError("simulated database failure")

    with pytest.raises(SQLAlchemyError):
        ingest_scheme(db, make_input())

    db.rollback.assert_called_once()


def test_schema_rejects_non_https_source():
    with pytest.raises(ValueError):
        make_input(source_url="http://example.gov.in/scheme")


@pytest.fixture
def api_client():
    db = MagicMock()
    db.scalar.return_value = None

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: type(
        "User", (), {"uid": "test-user"}
    )()

    with TestClient(app) as client:
        yield client, db

    app.dependency_overrides.clear()


def valid_payload(**overrides):
    payload = {
        "slug": "api-test-scheme",
        "title": "API Test Scheme",
        "administering_authority": "Test Authority",
        "government_level": "central",
        "language": "en",
        "description": "A scheme for API testing",
        "benefits": ["Education support"],
        "eligibility_criteria": {"minimum_age": 18},
        "required_documents": ["Identity proof"],
        "application_process": ["Submit an application"],
        "source_url": "https://example.gov.in/scheme",
        "publisher": "Test Authority",
    }
    payload.update(overrides)
    return payload


def test_ingestion_api_rejects_unauthenticated_request():
    client = TestClient(app)

    response = client.post(
        "/ingestion/schemes",
        json=valid_payload(),
    )

    assert response.status_code == 401


def test_ingestion_api_rejects_invalid_source(api_client):
    client, _ = api_client

    response = client.post(
        "/ingestion/schemes",
        json=valid_payload(source_url="http://example.gov.in/scheme"),
    )

    assert response.status_code == 422


def test_ingestion_api_returns_conflict_for_duplicate_slug(api_client):
    client, db = api_client
    db.scalar.return_value = Scheme(
        id=uuid4(),
        slug="api-test-scheme",
        title="Existing Scheme",
    )

    response = client.post(
        "/ingestion/schemes",
        json=valid_payload(),
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_ingestion_api_rolls_back_on_database_error(api_client):
    client, db = api_client
    db.scalar.return_value = None
    db.flush.side_effect = SQLAlchemyError("simulated database failure")

    response = client.post(
        "/ingestion/schemes",
        json=valid_payload(),
    )

    assert response.status_code == 500
    db.rollback.assert_called()


def test_ingestion_api_rejects_unknown_fields(api_client):
    client, _ = api_client

    response = client.post(
        "/ingestion/schemes",
        json=valid_payload(unexpected_field="not allowed"),
    )

    assert response.status_code == 422


def test_content_hash_is_generated_by_janvaani():
    import hashlib
    import json

    from app.ingestion.service import ingest_scheme

    db = MagicMock()
    db.scalar.return_value = None

    data = make_input(content_hash="caller-supplied-fake-hash")

    ingest_scheme(db, data)

    # The third database object added is the source document.
    source = db.add.call_args_list[2].args[0]

    expected_content = {
        "slug": data.slug,
        "title": data.title,
        "administering_authority": data.administering_authority,
        "government_level": data.government_level,
        "language": data.language,
        "description": data.description,
        "benefits": data.benefits,
        "eligibility_criteria": data.eligibility_criteria,
        "required_documents": data.required_documents,
        "application_process": data.application_process,
        "valid_from": data.valid_from.isoformat() if data.valid_from else None,
        "valid_until": data.valid_until.isoformat() if data.valid_until else None,
    }

    canonical = json.dumps(
        expected_content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    assert source.content_hash == expected_hash
    assert source.content_hash != "caller-supplied-fake-hash"


def test_version_flush_failure_rolls_back():
    db = MagicMock()
    db.scalar.return_value = None

    # The scheme flush succeeds; the version flush fails.
    db.flush.side_effect = [
        None,
        SQLAlchemyError("simulated version failure"),
    ]

    with pytest.raises(SQLAlchemyError, match="version failure"):
        ingest_scheme(db, make_input())

    assert db.add.call_count == 2
    assert db.flush.call_count == 2
    db.rollback.assert_called_once()


def test_source_flush_failure_rolls_back():
    db = MagicMock()
    db.scalar.return_value = None

    # Scheme and version flushes succeed; source flush fails.
    db.flush.side_effect = [
        None,
        None,
        SQLAlchemyError("simulated source failure"),
    ]

    with pytest.raises(SQLAlchemyError, match="source failure"):
        ingest_scheme(db, make_input())

    assert db.add.call_count == 3
    assert db.flush.call_count == 3
    db.rollback.assert_called_once()
