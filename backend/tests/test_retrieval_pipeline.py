
from uuid import uuid4
from unittest.mock import patch

import pytest

from app.retrieval.pipeline import search_scheme_records
from app.retrieval.repository import SchemeRecord


@pytest.fixture
def sample_record():
    return SchemeRecord(
        scheme_id=uuid4(),
        scheme_slug="sample-scholarship",
        scheme_title="Sample Scholarship",
        scheme_version_id=uuid4(),
        version_number=1,
        language="en",
        source_document_id=uuid4(),
        source_url="https://example.gov.in/scholarship",
        publisher="Synthetic test publisher",
        content=(
            "Description: Scholarship for eligible students. "
            "Benefits: Financial assistance for education. "
            "Eligibility: Students must meet the income criteria."
        ),
    )


def test_search_returns_ranked_result_with_provenance(sample_record):
    with patch(
        "app.retrieval.pipeline.load_searchable_scheme_records",
        return_value=[sample_record],
    ):
        results = search_scheme_records(
            db=None,
            query="scholarship financial assistance",
        )

    assert len(results) == 1
    assert results[0].record.scheme_slug == "sample-scholarship"
    assert results[0].result.chunk.source_url == sample_record.source_url
    assert results[0].result.chunk.source_review_status == "verified"
    assert results[0].result.chunk.scheme_review_status == "approved"
    assert results[0].result.score > 0


def test_search_returns_empty_for_unmatched_query(sample_record):
    with patch(
        "app.retrieval.pipeline.load_searchable_scheme_records",
        return_value=[sample_record],
    ):
        results = search_scheme_records(
            db=None,
            query="volcanic eruption",
        )

    assert results == []


def test_search_passes_language_and_slug_filters(sample_record):
    with patch(
        "app.retrieval.pipeline.load_searchable_scheme_records",
        return_value=[sample_record],
    ) as loader:
        search_scheme_records(
            db=None,
            query="scholarship",
            language="en",
            scheme_slug="sample-scholarship",
        )

    loader.assert_called_once_with(
        None,
        language="en",
        scheme_slug="sample-scholarship",
    )


def test_search_rejects_invalid_limit():
    with pytest.raises(ValueError, match="limit must be at least 1"):
        search_scheme_records(db=None, query="scholarship", limit=0)


def test_search_rejects_invalid_chunk_size():
    with pytest.raises(ValueError, match="chunk_size must be positive"):
        search_scheme_records(
            db=None,
            query="scholarship",
            chunk_size=0,
        )
