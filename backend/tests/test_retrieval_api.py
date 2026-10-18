
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def make_search_result():
    record = SimpleNamespace(
        scheme_id=uuid4(),
        scheme_slug="sample-scholarship",
        scheme_title="Sample Scholarship",
        scheme_version_id=uuid4(),
        version_number=1,
        language="en",
        source_document_id=uuid4(),
        source_url="https://example.gov.in/scholarship",
        publisher="Synthetic test publisher",
        content_type="scheme_record",
        source_review_status="verified",
        scheme_review_status="approved",
    )

    chunk = SimpleNamespace(
        chunk_id=0,
        text="Scholarship provides financial assistance to eligible students.",
        source_url=record.source_url,
        source_review_status="verified",
        scheme_review_status="approved",
    )

    return SimpleNamespace(
        record=record,
        result=SimpleNamespace(chunk=chunk, score=3),
    )


@patch("app.api.retrieval.search_scheme_records")
def test_search_returns_ranked_results(mock_search):
    mock_search.return_value = [make_search_result()]

    response = client.get(
        "/api/retrieval/search",
        params={"q": "scholarship", "language": "en", "limit": 5},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["query"] == "scholarship"
    assert body["result_count"] == 1
    assert len(body["results"]) == 1

    result = body["results"][0]
    assert result["scheme_slug"] == "sample-scholarship"
    assert result["source_url"] == "https://example.gov.in/scholarship"
    assert result["source_review_status"] == "verified"
    assert result["scheme_review_status"] == "approved"
    assert result["score"] == 3

    mock_search.assert_called_once()
    assert mock_search.call_args.kwargs["language"] == "en"
    assert mock_search.call_args.kwargs["limit"] == 5


@patch("app.api.retrieval.search_scheme_records")
def test_search_returns_empty_results(mock_search):
    mock_search.return_value = []

    response = client.get(
        "/api/retrieval/search",
        params={"q": "no matching scheme"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "no matching scheme",
        "result_count": 0,
        "results": [],
    }


def test_search_rejects_missing_query():
    response = client.get("/api/retrieval/search")

    assert response.status_code == 422


def test_search_rejects_query_longer_than_limit():
    response = client.get(
        "/api/retrieval/search",
        params={"q": "a" * 301},
    )

    assert response.status_code == 422


def test_search_rejects_invalid_result_limit():
    response = client.get(
        "/api/retrieval/search",
        params={"q": "scholarship", "limit": 0},
    )

    assert response.status_code == 422
