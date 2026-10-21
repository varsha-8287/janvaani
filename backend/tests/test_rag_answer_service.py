
from unittest.mock import MagicMock, patch

from app.retrieval.answer_service import (
    INSUFFICIENT_EVIDENCE,
    answer_from_evidence,
)


def trusted_evidence():
    return [
        {
            "scheme_title": "Test scheme",
            "source_url": "https://example.gov.in/test",
            "publisher": "Test authority",
            "version_number": 1,
            "content": "This is explicitly synthetic test content.",
            "source_review_status": "verified",
            "scheme_review_status": "approved",
        }
    ]


def test_returns_insufficient_evidence_when_empty():
    result = answer_from_evidence("Who can apply?", [])

    assert result["answer"] == INSUFFICIENT_EVIDENCE
    assert result["sources"] == []
    assert result["generated_by"] == "fallback"


def test_rejects_unreviewed_evidence():
    evidence = trusted_evidence()
    evidence[0]["source_review_status"] = "pending"

    result = answer_from_evidence("Who can apply?", evidence)

    assert result["answer"] == INSUFFICIENT_EVIDENCE
    assert result["sources"] == []


@patch.dict("os.environ", {"GEMINI_API_KEY": ""})
def test_returns_fallback_when_api_key_is_missing():
    result = answer_from_evidence("Who can apply?", trusted_evidence())

    assert result["answer"] == INSUFFICIENT_EVIDENCE
    assert result["generated_by"] == "fallback"


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
@patch("app.retrieval.answer_service.genai.Client")
def test_generates_answer_and_returns_source_metadata(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.return_value.text = (
        "The reviewed evidence describes the scheme. [Source 1]"
    )

    result = answer_from_evidence("Tell me about the scheme", trusted_evidence())

    assert result["generated_by"] == "gemini"
    assert "[Source 1]" in result["answer"]
    assert result["sources"][0]["source_url"] == "https://example.gov.in/test"

@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
@patch("app.retrieval.answer_service.genai.Client")
def test_rejects_answer_without_source_citation(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.return_value.text = (
        "The scheme provides assistance to applicants."
    )

    result = answer_from_evidence("Tell me about the scheme", trusted_evidence())

    assert result["generated_by"] == "fallback"
    assert result["answer"] == INSUFFICIENT_EVIDENCE
    assert result["sources"] == []


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
@patch("app.retrieval.answer_service.genai.Client")
def test_rejects_unknown_source_citation(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.return_value.text = (
        "The scheme provides assistance. [Source 99]"
    )

    result = answer_from_evidence("Tell me about the scheme", trusted_evidence())

    assert result["generated_by"] == "fallback"
    assert result["answer"] == INSUFFICIENT_EVIDENCE
    assert result["sources"] == []
