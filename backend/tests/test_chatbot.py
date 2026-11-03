
from unittest.mock import patch

from app.chatbot.service import chat
from app.retrieval.answer_service import INSUFFICIENT_EVIDENCE


def test_chat_uses_retrieved_evidence_and_returns_sources():
    with (
        patch("app.chatbot.service.search_scheme_records", return_value=[]),
        patch(
            "app.chatbot.service.answer_from_evidence",
            return_value={
                "answer": "See the reviewed scheme details. [Source 1]",
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
        ) as answer_mock,
    ):
        result = chat(None, "Tell me about this scheme")

    assert result["generated_by"] == "gemini"
    assert result["sources"][0]["id"] == 1
    answer_mock.assert_called_once_with("Tell me about this scheme", [])


def test_chat_returns_fallback_without_evidence():
    with (
        patch("app.chatbot.service.search_scheme_records", return_value=[]),
        patch(
            "app.chatbot.service.answer_from_evidence",
            return_value={
                "answer": INSUFFICIENT_EVIDENCE,
                "generated_by": "fallback",
                "sources": [],
            },
        ),
        patch(
            "app.chatbot.service.generate_gemini_direct_answer",
            return_value={
                "answer": INSUFFICIENT_EVIDENCE,
                "generated_by": "fallback",
                "sources": [],
            },
        ),
    ):
        result = chat(None, "Unknown scheme")

    assert result["answer"] == INSUFFICIENT_EVIDENCE
    assert result["sources"] == []


def test_chat_uses_gemini_direct_when_evidence_is_insufficient():
    with (
        patch("app.chatbot.service.search_scheme_records", return_value=[]),
        patch(
            "app.chatbot.service.answer_from_evidence",
            return_value={
                "answer": INSUFFICIENT_EVIDENCE,
                "generated_by": "fallback",
                "sources": [],
            },
        ),
        patch(
            "app.chatbot.service.generate_gemini_direct_answer",
            return_value={
                "answer": "Here is helpful information about the scheme provided by Gemini.",
                "generated_by": "gemini",
                "sources": [],
            },
        ) as gemini_mock,
    ):
        result = chat(None, "Tell me about women schemes")

    assert result["generated_by"] == "gemini"
    assert "Gemini" in result["answer"]
    gemini_mock.assert_called_once()



def test_chat_uses_history_to_build_follow_up_retrieval_query():
    history = [
        {"role": "user", "content": "Tell me about scholarships"},
        {"role": "assistant", "content": "Which part would you like to know?"},
    ]

    with (
        patch("app.chatbot.service.search_scheme_records", return_value=[]) as search_mock,
        patch(
            "app.chatbot.service.answer_from_evidence",
            return_value={
                "answer": INSUFFICIENT_EVIDENCE,
                "generated_by": "fallback",
                "sources": [],
            },
        ),
    ):
        chat(None, "What documents are needed?", history)

    query = search_mock.call_args.args[1]
    assert "scholarships" in query
    assert "What documents are needed?" in query


def test_chat_trims_question_and_limits_history():
    history = [
        {"role": "user", "content": f"old message {index}"}
        for index in range(10)
    ]

    with (
        patch("app.chatbot.service.search_scheme_records", return_value=[]) as search_mock,
        patch(
            "app.chatbot.service.answer_from_evidence",
            return_value={
                "answer": INSUFFICIENT_EVIDENCE,
                "generated_by": "fallback",
                "sources": [],
            },
        ),
    ):
        result = chat(None, "  Hello  ", history)

    assert result["question"] == "Hello"
    query = search_mock.call_args.args[1]
    assert "old message 0" not in query
    assert "old message 9" in query


def test_chat_propagates_language_to_search_and_answer():
    with (
        patch("app.chatbot.service.search_scheme_records", return_value=[]) as search_mock,
        patch(
            "app.chatbot.service.answer_from_evidence",
            return_value={
                "answer": "योजना का विवरण। [Source 1]",
                "generated_by": "gemini",
                "sources": [],
            },
        ) as answer_mock,
    ):
        result = chat(None, "योजना के बारे में बताएं", language="hi")

    assert result["answer"] == "योजना का विवरण। [Source 1]"
    assert search_mock.call_args.kwargs.get("language") == "hi"
    answer_mock.assert_called_once_with("योजना के बारे में बताएं", [], language="hi")

