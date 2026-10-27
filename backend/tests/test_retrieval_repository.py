
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.models import Scheme, SchemeVersion, SourceDocument
from app.retrieval.repository import load_searchable_scheme_records


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


def add_scheme_records(
    db: Session,
    *,
    scheme_status: str = "published",
    version_status: str = "approved",
    source_status: str = "verified",
    source_url: str = "https://example.gov.in/scholarship",
    language: str = "en",
    slug: str = "student-scholarship",
) -> tuple[Scheme, SchemeVersion, SourceDocument]:
    scheme = Scheme(
        id=uuid4(),
        slug=slug,
        title="Student Scholarship",
        government_level="central",
        status=scheme_status,
    )
    version = SchemeVersion(
        id=uuid4(),
        scheme_id=scheme.id,
        version_number=1,
        language=language,
        description="Scholarship assistance for eligible students.",
        benefits=["Education support"],
        eligibility_criteria={"age": "18 or older"},
        required_documents=["Identity proof"],
        application_process=["Apply online"],
        review_status=version_status,
    )
    source = SourceDocument(
        id=uuid4(),
        scheme_version_id=version.id,
        source_url=source_url,
        publisher="Test publisher",
        retrieved_at=datetime.now(timezone.utc),
        review_status=source_status,
    )

    db.add_all([scheme, version, source])
    db.flush()
    return scheme, version, source


def test_loads_published_approved_verified_records(db):
    scheme, version, source = add_scheme_records(db)

    results = load_searchable_scheme_records(db)

    assert len(results) == 1
    result = results[0]
    assert result.scheme_id == scheme.id
    assert result.scheme_version_id == version.id
    assert result.source_document_id == source.id
    assert result.source_url == source.source_url
    assert result.content_type == "scheme_record"
    assert "Scholarship assistance" in result.content


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scheme_status", "draft"),
        ("version_status", "pending_review"),
        ("version_status", "rejected"),
        ("source_status", "pending"),
        ("source_status", "rejected"),
    ],
)
def test_excludes_unpublished_or_unverified_records(db, field, value):
    kwargs = {field: value}
    add_scheme_records(db, **kwargs)

    assert load_searchable_scheme_records(db) == []


@pytest.mark.parametrize(
    "source_url",
    [
        "javascript:alert(1)",
        "ftp://example.gov.in/file",
        "",
    ],
)
def test_excludes_invalid_source_urls(db, source_url):
    add_scheme_records(db, source_url=source_url)

    assert load_searchable_scheme_records(db) == []


def test_filters_by_language(db):
    add_scheme_records(db, language="en", slug="english-scheme")
    add_scheme_records(db, language="ta", slug="tamil-scheme")

    results = load_searchable_scheme_records(db, language="ta")

    assert len(results) == 1
    assert results[0].language == "ta"
    assert results[0].scheme_slug == "tamil-scheme"


def test_filters_by_scheme_slug(db):
    add_scheme_records(db, slug="scheme-one")
    add_scheme_records(db, slug="scheme-two")

    results = load_searchable_scheme_records(db, scheme_slug="scheme-two")

    assert len(results) == 1
    assert results[0].scheme_slug == "scheme-two"
