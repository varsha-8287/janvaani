
"""Read-only pipeline connecting scheme records to keyword retrieval."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.retrieval.repository import (
    SchemeRecord,
    load_searchable_scheme_records,
)
from app.retrieval.service import (
    RetrievedChunk,
    TextChunk,
    chunk_text,
    retrieve_trusted_chunks,
)


@dataclass(frozen=True)
class SchemeSearchResult:
    """A ranked chunk with its associated scheme-record metadata."""

    record: SchemeRecord
    result: RetrievedChunk


def search_scheme_records(
    db: Session,
    query: str,
    *,
    language: str | None = None,
    scheme_slug: str | None = None,
    limit: int = 5,
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[SchemeSearchResult]:
    """Search approved scheme records without modifying the database."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    # Validate chunking settings even when no records are available.
    chunk_text("", chunk_size=chunk_size, overlap=overlap)

    records = load_searchable_scheme_records(
        db,
        language=language,
        scheme_slug=scheme_slug,
    )

    chunks: list[TextChunk] = []
    records_by_chunk_id: dict[int, SchemeRecord] = {}
    next_chunk_id = 0

    for record in records:
        record_chunks = chunk_text(
            record.content,
            chunk_size=chunk_size,
            overlap=overlap,
            source_url=record.source_url,
            source_review_status=record.source_review_status,
            scheme_review_status=record.scheme_review_status,
        )

        for chunk in record_chunks:
            # Use globally unique IDs so each chunk maps to its own record.
            identified_chunk = TextChunk(
                chunk_id=next_chunk_id,
                text=chunk.text,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                source_url=chunk.source_url,
                source_review_status=chunk.source_review_status,
                scheme_review_status=chunk.scheme_review_status,
            )
            chunks.append(identified_chunk)
            records_by_chunk_id[next_chunk_id] = record
            next_chunk_id += 1

    ranked_chunks = retrieve_trusted_chunks(
        query,
        chunks,
        limit=limit,
    )

    return [
        SchemeSearchResult(
            record=records_by_chunk_id[item.chunk.chunk_id],
            result=item,
        )
        for item in ranked_chunks
    ]
