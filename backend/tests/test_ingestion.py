
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.database.models import Scheme
from app.ingestion.schemas import SchemeIngestionInput
from app.ingestion.service import DuplicateSchemeError, ingest_scheme


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
