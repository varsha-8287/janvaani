
"""Question-answering API grounded in reviewed scheme retrieval results."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.retrieval.answer_service import answer_from_evidence
from app.retrieval.pipeline import search_scheme_records

router = APIRouter(prefix="/api/rag", tags=["RAG"])


class SourceReference(BaseModel):
    id: int
    scheme_title: str
    source_url: str
    publisher: str | None = None
    version_number: int | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    generated_by: str
    sources: list[SourceReference]


@router.get("/ask", response_model=AskResponse)
def ask_question(
    q: str = Query(..., min_length=1, max_length=500),
    language: str | None = Query(default=None, min_length=2, max_length=20),
    limit: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_db),
) -> AskResponse:
    """Answer a question from reviewed scheme records."""
    results = search_scheme_records(
        db,
        q,
        language=language,
        limit=limit,
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

    result = answer_from_evidence(q, evidence)

    return AskResponse(
        question=q,
        answer=result["answer"],
        generated_by=result["generated_by"],
        sources=result["sources"],
    )
