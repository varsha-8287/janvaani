import os
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.database.models import Scheme, SchemeVersion, SourceDocument
from app.ingestion.schemas import SchemeIngestionInput
from app.ingestion.service import DuplicateSchemeError, ingest_scheme


TEST_DATABASE_URL = os.getenv("JANVAANI_TEST_DATABASE_URL")


def validate_test_database_url(url: str) -> None:
    """Reject URLs that do not target the dedicated local test database."""
    from sqlalchemy.engine import make_url

    parsed = make_url(url)

    if (
        parsed.get_backend_name() != "postgresql"
        or parsed.host != "127.0.0.1"
        or parsed.port != 5432
        or parsed.database != "janvaani_test"
        or parsed.username != "janvaani_test"
    ):
        raise RuntimeError(
            "Integration tests require the dedicated local "
            "janvaani_test database at 127.0.0.1:5433."
        )


@pytest.fixture(scope="module")
def test_engine():
    """Connect only to the explicitly configured local test database."""
    if not TEST_DATABASE_URL:
        pytest.skip(
            "Set JANVAANI_TEST_DATABASE_URL to run PostgreSQL integration tests."
        )

    validate_test_database_url(TEST_DATABASE_URL)

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            database, port = connection.execute(
                select(
                    func.current_database(),
                    func.current_setting("port"),
                )
            ).one()

            if database != "janvaani_test" or int(port) != 5432:
                raise RuntimeError(
                    "Connected PostgreSQL server is not the expected test database."
                )
    except Exception:
        engine.dispose()
        raise

    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Wrap each test in an outer transaction that is always rolled back."""
    Session = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        join_transaction_mode="create_savepoint",
    )

    connection = test_engine.connect()
    outer_transaction = connection.begin()

    try:
        with Session(bind=connection) as session:
            yield session
    finally:
        if outer_transaction.is_active:
            outer_transaction.rollback()
        connection.close()


def make_input(**overrides):
    """Build valid ingestion data with a unique slug for each test."""
    values = {
        "slug": f"integration-{uuid4().hex}",
        "title": "Integration Test Scheme",
        "government_level": "central",
        "language": "en",
        "description": "Testing real PostgreSQL persistence.",
        "benefits": ["Education support"],
        "eligibility_criteria": {"minimum_age": 18},
        "required_documents": ["Identity proof"],
        "application_process": ["Submit an application"],
        "source_url": "https://example.gov.in/integration-test",
        "publisher": "Integration Test Authority",
        "retrieved_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return SchemeIngestionInput(**values)


def test_successful_ingestion_persists_all_records(db_session):
    """Persist and verify the scheme, first version, and source document."""
    data = make_input()

    scheme = ingest_scheme(db_session, data)
    db_session.commit()

    stored_scheme = db_session.scalar(
        select(Scheme).where(Scheme.slug == data.slug)
    )

    assert stored_scheme is not None
    assert stored_scheme.title == data.title
    assert stored_scheme.status == "draft"

    versions = db_session.scalars(
        select(SchemeVersion).where(
            SchemeVersion.scheme_id == stored_scheme.id
        )
    ).all()

    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].review_status == "draft"

    sources = db_session.scalars(
        select(SourceDocument).where(
            SourceDocument.scheme_version_id == versions[0].id
        )
    ).all()

    assert len(sources) == 1
    assert sources[0].source_url == data.source_url
    assert sources[0].review_status == "pending"
    assert sources[0].content_hash is not None
    assert len(sources[0].content_hash) == 64


def test_duplicate_slug_is_rejected_without_extra_records(db_session):
    """Reject duplicate slugs without creating additional rows."""
    data = make_input()

    ingest_scheme(db_session, data)
    db_session.flush()

    with pytest.raises(DuplicateSchemeError):
        ingest_scheme(db_session, data)

    count = db_session.scalar(
        select(func.count())
        .select_from(Scheme)
        .where(Scheme.slug == data.slug)
    )

    assert count == 1


def test_write_failure_rolls_back_all_ingestion_records(
    db_session, monkeypatch
):
    """Verify a failure on the source write rolls back earlier writes."""
    data = make_input()

    original_flush = db_session.flush
    flush_count = 0

    def fail_on_third_flush(*args, **kwargs):
        nonlocal flush_count
        flush_count += 1

        if flush_count == 3:
            raise SQLAlchemyError("Simulated source-document write failure")

        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db_session, "flush", fail_on_third_flush)

    with pytest.raises(SQLAlchemyError, match="Simulated source-document"):
        ingest_scheme(db_session, data)

    # The service should roll back its transaction after the failure.
    scheme_count = db_session.scalar(
        select(func.count())
        .select_from(Scheme)
        .where(Scheme.slug == data.slug)
    )
    version_count = db_session.scalar(
        select(func.count()).select_from(SchemeVersion)
    )
    source_count = db_session.scalar(
        select(func.count()).select_from(SourceDocument)
    )

    assert scheme_count == 0
    assert version_count == 0
    assert source_count == 0


def test_ingestion_creates_draft_scheme_and_pending_source():
    db = MagicMock()
    db.scalar.return_value = None

    data = make_input()
    scheme = ingest_scheme(db, data)

    added_objects = [
        call.args[0] for call in db.add.call_args_list
    ]
    version = added_objects[1]
    source = added_objects[2]

    assert scheme.status == "draft"
    assert version.version_number == 1
    assert version.review_status == "draft"

    assert source.source_url == data.source_url
    assert source.publisher == data.publisher
    assert source.language == data.language
    assert source.review_status == "pending"
    assert source.retrieved_at == data.retrieved_at


def test_ingestion_content_hash_is_stable_for_same_input():
    first_db = MagicMock()
    first_db.scalar.return_value = None

    second_db = MagicMock()
    second_db.scalar.return_value = None

    data = make_input()

    ingest_scheme(first_db, data)
    ingest_scheme(second_db, data)

    first_source = first_db.add.call_args_list[2].args[0]
    second_source = second_db.add.call_args_list[2].args[0]

    assert first_source.content_hash == second_source.content_hash
