
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.database.session import get_db
from app.retrieval.answer_service import INSUFFICIENT_EVIDENCE

client = TestClient(app)


def test_ask_returns_answer_and_sources():
    with (
        patch("app.api.ask.search_scheme_records", return_value=[]),
        patch(
            "app.api.ask.answer_from_evidence",
            return_value={
                "answer": "The reviewed evidence describes this scheme. [Source 1]",
                "generated_by": "gemini",
                "sources": [
                    {
                        "id": 1,
                        "scheme_title": "Test scheme",
                        "source_url": "https://example.gov.in/test",
                        "publisher": "Test authority",
                        "version_number": 1,
                    }
                ],
            },
        ),
    ):
        response = client.get("/api/rag/ask", params={"q": "Tell me about a scheme"})

    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "Tell me about a scheme"
    assert body["generated_by"] == "gemini"
    assert body["sources"][0]["source_url"] == "https://example.gov.in/test"


def test_ask_returns_fallback_when_no_evidence():
    with (
        patch("app.api.ask.search_scheme_records", return_value=[]),
        patch(
            "app.api.ask.answer_from_evidence",
            return_value={
                "answer": INSUFFICIENT_EVIDENCE,
                "generated_by": "fallback",
                "sources": [],
            },
        ),
    ):
        response = client.get("/api/rag/ask", params={"q": "Unknown scheme"})

    assert response.status_code == 200
    assert response.json()["answer"] == INSUFFICIENT_EVIDENCE
    assert response.json()["sources"] == []


def test_ask_rejects_empty_question():
    response = client.get("/api/rag/ask", params={"q": ""})

    assert response.status_code == 422


def test_ask_rejects_question_longer_than_500_characters():
    response = client.get("/api/rag/ask", params={"q": "a" * 501})

    assert response.status_code == 422


def test_ask_rejects_invalid_limit():
    response = client.get(
        "/api/rag/ask",
        params={"q": "scholarship", "limit": 0},
    )

    assert response.status_code == 422
