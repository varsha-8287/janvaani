
"""Stateless chatbot orchestration using existing RAG retrieval."""

from typing import Any

from sqlalchemy.orm import Session

from app.retrieval.answer_service import (
    INSUFFICIENT_EVIDENCE,
    answer_from_evidence,
    generate_gemini_direct_answer,
)
from app.retrieval.pipeline import search_scheme_records


MAX_HISTORY_TURNS = 6


def chat(
    db: Session,
    question: str,
    history: list[dict[str, str]] | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """Answer a chat question using reviewed scheme evidence and Gemini.

    If database evidence is available and reviewed, answers are evidence-grounded.
    If database evidence is sparse or conversational, Gemini answers directly
    using official scheme knowledge without refusing.
    """
    question = question.strip()
    recent_history = (history or [])[-MAX_HISTORY_TURNS:]

    context_lines = []
    for turn in recent_history:
        role = turn.get("role")
        content = turn.get("content", "").strip()
        if role in {"user", "assistant"} and content:
            context_lines.append(f"{role}: {content[:1000]}")

    retrieval_query = question
    if context_lines:
        retrieval_query = (
            "Conversation context (for interpreting the question only):\n"
            + "\n".join(context_lines)
            + f"\nCurrent question: {question}"
        )

    results = search_scheme_records(
        db,
        retrieval_query,
        language=language,
        limit=5,
    )

    evidence = [
        {
            "scheme_title": item.record.scheme_title,
            "source_url": item.record.source_url,
            "publisher": item.record.publisher,
            "version_number": item.record.version_number,
            "content": item.result.chunk.text,
            "source_review_status": item.result.chunk.source_review_status,
            "scheme_review_status": item.result.chunk.scheme_review_status,
        }
        for item in results
    ]

    # 1. Attempt strict evidence-grounded answer if evidence is present
    if language:
        result = answer_from_evidence(question, evidence, language=language)
    else:
        result = answer_from_evidence(question, evidence)

    # 2. If evidence was insufficient or lacking citation, fall back to Gemini direct answering
    if result.get("answer") == INSUFFICIENT_EVIDENCE:
        gemini_result = generate_gemini_direct_answer(
            question=question,
            history=recent_history,
            language=language,
            evidence=evidence,
        )
        if gemini_result.get("answer") and gemini_result["answer"] != INSUFFICIENT_EVIDENCE:
            result = gemini_result

    return {
        "question": question,
        "answer": result["answer"],
        "generated_by": result["generated_by"],
        "sources": result["sources"],
    }

