
"""Deterministic validation of extracted document evidence."""
from collections.abc import Mapping
from typing import Any

from app.documents.schemas import (
    DocumentValidationResult,
    EvidenceReference,
    ExtractedDocument,
    FieldIssue,
)


# Only apply formats when the document type and field meaning are known.
# Extend this registry when verified document formats are available.
FIELD_FORMATS: dict[tuple[str, str], str] = {
    ("income_certificate", "annual_income"): "non_negative_number",
    ("income_certificate", "issue_date"): "iso_date",
    ("land_record", "land_hectares"): "non_negative_number",
    ("land_record", "issue_date"): "iso_date",
    ("identity_proof", "issue_date"): "iso_date",
}


def _evidence(
    document: ExtractedDocument,
    field_name: str,
) -> EvidenceReference:
    return EvidenceReference(
        document_id=document.document_id,
        document_type=document.document_type,
        field_name=field_name,
    )


def validate_document(
    document: ExtractedDocument,
    *,
    required_fields: set[str] | None = None,
) -> DocumentValidationResult:
    """Validate known field formats and explicitly report missing fields.

    This function does not perform OCR or determine document authenticity.
    Unknown formats are left unvalidated rather than guessed.
    """
    required = required_fields or set()
    issues: list[FieldIssue] = []

    for field_name in sorted(required):
        value = document.fields.get(field_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            issues.append(
                FieldIssue(
                    field_name=field_name,
                    status="MISSING",
                    explanation="A required extracted field is missing or blank.",
                    evidence=[],
                )
            )

    for field_name, value in document.fields.items():
        format_name = FIELD_FORMATS.get(
            (document.document_type, field_name)
        )
        if format_name is None or value is None:
            continue

        valid = True
        if format_name == "non_negative_number":
            # Reject booleans even though bool is a subclass of int.
            valid = (
                not isinstance(value, bool)
                and isinstance(value, (int, float))
                and value >= 0
            )
        elif format_name == "iso_date":
            if not isinstance(value, str):
                valid = False
            else:
                from datetime import date

                try:
                    date.fromisoformat(value)
                except ValueError:
                    valid = False

        if not valid:
            issues.append(
                FieldIssue(
                    field_name=field_name,
                    status="INVALID",
                    explanation=(
                        "The extracted value does not match the configured "
                        "field format. Verify it against the original document."
                    ),
                    evidence=[_evidence(document, field_name)],
                )
            )

    return DocumentValidationResult(
        document_id=document.document_id,
        document_type=document.document_type,
        valid=not issues,
        issues=issues,
    )


def detect_profile_conflicts(
    document: ExtractedDocument,
    profile: Mapping[str, Any],
    *,
    comparable_fields: set[str],
) -> list[FieldIssue]:
    """Report differing non-empty claims without selecting a winning value.

    Field names must be explicitly allow-listed by the caller. Values are
    compared exactly; normalization should be field-specific and reviewed.
    """
    issues: list[FieldIssue] = []

    for field_name in sorted(comparable_fields):
        document_value = document.fields.get(field_name)
        profile_value = profile.get(field_name)

        if document_value is None or profile_value is None:
            continue
        if isinstance(document_value, str) and not document_value.strip():
            continue
        if isinstance(profile_value, str) and not profile_value.strip():
            continue
        if document_value == profile_value:
            continue

        issues.append(
            FieldIssue(
                field_name=field_name,
                status="CONFLICT",
                explanation=(
                    "The document claim differs from the profile claim. "
                    "Review both sources; neither value was chosen automatically."
                ),
                evidence=[_evidence(document, field_name)],
            )
        )

    return issues
