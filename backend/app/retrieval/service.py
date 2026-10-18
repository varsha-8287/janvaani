
"""Lightweight text chunking and keyword retrieval for scheme documents."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TextChunk:
    """A searchable section of a source document."""

    chunk_id: int
    text: str
    start_offset: int
    end_offset: int
    source_url: str | None = None
    source_review_status: str = "pending"
    scheme_review_status: str = "draft"


@dataclass(frozen=True)
class RetrievedChunk:
    """A retrieved text chunk with a relevance score."""

    chunk: TextChunk
    score: int


def chunk_text(
    text: str,
    *,
    chunk_size: int = 800,
    overlap: int = 120,
    source_url: str | None = None,
    source_review_status: str = "pending",
    scheme_review_status: str = "draft",
) -> list[TextChunk]:
    """Split text into overlapping character chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        content = text[start:end].strip()
        if content:
            chunks.append(
                TextChunk(
                    chunk_id=len(chunks),
                    text=content,
                    start_offset=start,
                    end_offset=end,
                    source_url=source_url,
                    source_review_status=source_review_status,
                    scheme_review_status=scheme_review_status,
                )
            )

        if end >= len(text):
            break

        next_start = end - overlap
        start = next_start if next_start > start else end

    return chunks


def retrieve_chunks(
    query: str,
    chunks: list[TextChunk],
    *,
    limit: int = 5,
) -> list[RetrievedChunk]:
    """Rank chunks by keyword overlap; this is not semantic search."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    terms = set(re.findall(r"\w+", query.casefold()))
    terms = {term for term in terms if len(term) > 1}

    if not terms:
        return []

    results = []

    for chunk in chunks:
        words = re.findall(r"\w+", chunk.text.casefold())
        score = sum(1 for word in words if word in terms)

        if score:
            results.append(RetrievedChunk(chunk=chunk, score=score))

    results.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
    return results[:limit]


def retrieve_trusted_chunks(
    query: str,
    chunks: list[TextChunk],
    *,
    limit: int = 5,
) -> list[RetrievedChunk]:
    """Retrieve evidence only from verified sources and approved versions."""
    trusted_chunks = [
        chunk
        for chunk in chunks
        if chunk.source_review_status == "verified"
        and chunk.scheme_review_status == "approved"
        and chunk.source_url
        and chunk.source_url.startswith(("https://", "http://"))
    ]

    return retrieve_chunks(query, trusted_chunks, limit=limit)

