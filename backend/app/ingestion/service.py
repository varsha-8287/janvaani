
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Scheme, SchemeVersion, SourceDocument
from app.ingestion.schemas import SchemeIngestionInput


class DuplicateSchemeError(ValueError):
    """Raised when a scheme slug already exists."""


def ingest_scheme(
    db: Session,
    data: SchemeIngestionInput,
) -> Scheme:
    """Store a new scheme, its first version, and its source atomically.

    Ingested content remains a draft until an authorized reviewer approves it.
    The caller owns the session and transaction.
    """
    existing = db.scalar(
        select(Scheme).where(Scheme.slug == data.slug)
    )
    if existing is not None:
        raise DuplicateSchemeError(
            f"A scheme with slug '{data.slug}' already exists."
        )

    content = {
        "slug": data.slug,
        "title": data.title,
        "administering_authority": data.administering_authority,
        "government_level": data.government_level,
        "language": data.language,
        "description": data.description,
        "benefits": data.benefits,
        "eligibility_criteria": data.eligibility_criteria,
        "required_documents": data.required_documents,
        "application_process": data.application_process,
        "valid_from": data.valid_from.isoformat() if data.valid_from else None,
        "valid_until": data.valid_until.isoformat() if data.valid_until else None,
    }
    canonical_content = json.dumps(
        content, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    content_hash = data.content_hash or hashlib.sha256(
        canonical_content.encode("utf-8")
    ).hexdigest()

    try:
        scheme = Scheme(
            slug=data.slug,
            title=data.title,
            administering_authority=data.administering_authority,
            government_level=data.government_level,
            status="draft",
        )
        db.add(scheme)
        db.flush()

        version = SchemeVersion(
            scheme_id=scheme.id,
            version_number=1,
            language=data.language,
            description=data.description,
            benefits=data.benefits,
            eligibility_criteria=data.eligibility_criteria,
            required_documents=data.required_documents,
            application_process=data.application_process,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            review_status="draft",
        )
        db.add(version)
        db.flush()

        source = SourceDocument(
            scheme_version_id=version.id,
            source_url=data.source_url,
            publisher=data.publisher,
            retrieved_at=data.retrieved_at,
            content_hash=content_hash,
            language=data.language,
            review_status="pending",
        )
        db.add(source)
        db.flush()

        return scheme

    except Exception:
        db.rollback()
        raise
