
"""Read-only API for searching reviewed scheme records."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.retrieval.pipeline import search_scheme_records

router = APIRouter(
    prefix="/api/retrieval",
    tags=["Retrieval"],
)


class SchemeSearchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scheme_id: str
    scheme_slug: str
    scheme_title: str
    scheme_version_id: str
    version_number: int
    language: str
    source_document_id: str
    source_url: str
    publisher: str | None
    content: str
    content_type: str
    source_review_status: str
    scheme_review_status: str
    score: int


class SchemeSearchResponse(BaseModel):
    query: str
    result_count: int
    results: list[SchemeSearchItem]


@router.get("/search", response_model=SchemeSearchResponse)
def search_schemes(
    q: str = Query(
        ...,
        min_length=1,
        max_length=300,
        description="Keywords to search in reviewed scheme records",
    ),
    language: str | None = Query(default=None, min_length=2, max_length=20),
    scheme_slug: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> SchemeSearchResponse:
    """Search approved scheme records and return ranked matching chunks."""
    results = search_scheme_records(
        db,
        q,
        language=language,
        scheme_slug=scheme_slug,
        limit=limit,
    )

    items = [
        SchemeSearchItem(
            scheme_id=str(item.record.scheme_id),
            scheme_slug=item.record.scheme_slug,
            scheme_title=item.record.scheme_title,
            scheme_version_id=str(item.record.scheme_version_id),
            version_number=item.record.version_number,
            language=item.record.language,
            source_document_id=str(item.record.source_document_id),
            source_url=item.record.source_url,
            publisher=item.record.publisher,
            content=item.result.chunk.text,
            content_type=item.record.content_type,
            source_review_status=item.result.chunk.source_review_status,
            scheme_review_status=item.result.chunk.scheme_review_status,
            score=item.result.score,
        )
        for item in results
    ]

    return SchemeSearchResponse(
        query=q,
        result_count=len(items),
        results=items,
    )
