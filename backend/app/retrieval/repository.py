
"""Read-only database retrieval for approved Janvaani scheme records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.database.models import Scheme, SchemeVersion, SourceDocument


@dataclass(frozen=True)
class SchemeRecord:
    """Searchable scheme-record content with verified provenance metadata."""

    scheme_id: UUID
    scheme_slug: str
    scheme_title: str
    scheme_version_id: UUID
    version_number: int
    language: str
    source_document_id: UUID
    source_url: str
    publisher: str | None
    content: str
    content_type: str = "scheme_record"
    source_review_status: str = "verified"
    scheme_review_status: str = "approved"


def _json_text(value: object) -> str:
    """Convert a JSON-compatible value into readable searchable text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return ""


def _version_content(version: SchemeVersion) -> str:
    """Build searchable text from stored scheme fields, not source quotations."""
    fields = [
        ("Description", version.description),
        ("Benefits", _json_text(version.benefits)),
        ("Eligibility", _json_text(version.eligibility_criteria)),
        ("Required documents", _json_text(version.required_documents)),
        ("Application process", _json_text(version.application_process)),
    ]

    return "\n".join(
        f"{label}: {value}"
        for label, value in fields
        if value
    )


def load_searchable_scheme_records(
    db: Session,
    *,
    language: str | None = None,
    scheme_slug: str | None = None,
) -> list[SchemeRecord]:
    """Load records from published schemes with approved versions and verified sources.

    This function only reads database records. It does not claim that stored
    scheme fields are verbatim text from the linked source document.
    """
    stmt = (
        select(SourceDocument)
        .join(
            SchemeVersion,
            SourceDocument.scheme_version_id == SchemeVersion.id,
        )
        .join(Scheme, SchemeVersion.scheme_id == Scheme.id)
        .options(
            joinedload(SourceDocument.scheme_version).joinedload(
                SchemeVersion.scheme
            )
        )
        .where(Scheme.status == "published")
        .where(SchemeVersion.review_status == "approved")
        .where(SourceDocument.review_status == "verified")
        .where(
            or_(
                SourceDocument.source_url.startswith("https://"),
                SourceDocument.source_url.startswith("http://"),
            )
        )
        .order_by(Scheme.title, SchemeVersion.version_number)
    )

    if scheme_slug:
        stmt = stmt.where(Scheme.slug == scheme_slug)

    if language:
        lang_stmt = stmt.where(SchemeVersion.language == language)
        sources = db.scalars(lang_stmt).unique().all()
        if not sources:
            sources = db.scalars(stmt).unique().all()
    else:
        sources = db.scalars(stmt).unique().all()

    records: list[SchemeRecord] = []

    for source in sources:
        version = source.scheme_version
        scheme = version.scheme
        content = _version_content(version)

        if not content:
            continue

        records.append(
            SchemeRecord(
                scheme_id=scheme.id,
                scheme_slug=scheme.slug,
                scheme_title=scheme.title,
                scheme_version_id=version.id,
                version_number=version.version_number,
                language=version.language,
                source_document_id=source.id,
                source_url=source.source_url,
                publisher=source.publisher,
                content=content,
            )
        )

    return records
