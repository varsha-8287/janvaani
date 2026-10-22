
"""Evidence-based application document readiness checks."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.documents.schemas import ExtractedDocument


class ReadinessStatus(str, Enum):
    READY = "READY"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ApplicationReadinessResult(BaseModel):
    """Document checklist result, not a government eligibility decision."""

    status: ReadinessStatus
    required_documents: list[str] = Field(default_factory=list)
    submitted_documents: list[str] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    message: str
    authenticity_verified: bool = False


def _parse_required_documents(value: Any) -> list[str] | None:
    """Accept only the currently evidenced list-of-string format.

    None means requirements cannot safely be interpreted.
    An empty list is treated as insufficient evidence, not as proof
    that no documents are required.
    """
    if not isinstance(value, list) or not value:
        return None

    if any(not isinstance(item, str) or not item.strip() for item in value):
        return None

    # Preserve the approved requirement wording while removing duplicates
    # that differ only in capitalization or surrounding whitespace.
    unique: dict[str, str] = {}
    for item in value:
        cleaned = item.strip()
        unique.setdefault(cleaned.casefold(), cleaned)

    return list(unique.values())


def assess_application_readiness(
    required_documents: Any,
    submitted_documents: list[ExtractedDocument],
) -> ApplicationReadinessResult:
    """Compare submitted document types with approved scheme requirements.

    Only document-type presence is checked here. OCR quality, authenticity,
    scheme eligibility, and official application acceptance are not inferred.
    """
    required = _parse_required_documents(required_documents)

    submitted_by_key: dict[str, str] = {}
    for document in submitted_documents:
        cleaned = document.document_type.strip()
        if cleaned:
            submitted_by_key.setdefault(cleaned.casefold(), cleaned)

    submitted = list(submitted_by_key.values())

    if required is None:
        return ApplicationReadinessResult(
            status=ReadinessStatus.INSUFFICIENT_EVIDENCE,
            submitted_documents=submitted,
            message=(
                "Approved document requirements are missing, empty, or use "
                "an unsupported format. Readiness cannot be determined."
            ),
        )

    submitted_keys = set(submitted_by_key)
    missing = [
        item for item in required
        if item.casefold() not in submitted_keys
    ]

    if missing:
        return ApplicationReadinessResult(
            status=ReadinessStatus.NEEDS_ATTENTION,
            required_documents=required,
            submitted_documents=submitted,
            missing_documents=missing,
            message="One or more required document types have not been supplied.",
        )

    return ApplicationReadinessResult(
        status=ReadinessStatus.READY,
        required_documents=required,
        submitted_documents=submitted,
        message=(
            "All required document types are represented in the supplied "
            "evidence. This does not verify authenticity or eligibility."
        ),
    )
