
from app.applications.readiness import (
    ReadinessStatus,
    assess_application_readiness,
)
from app.documents.schemas import ExtractedDocument


def document(document_id: str, document_type: str) -> ExtractedDocument:
    return ExtractedDocument(
        document_id=document_id,
        document_type=document_type,
        fields={},
    )


def test_all_required_document_types_present():
    result = assess_application_readiness(
        ["Identity proof", "Income certificate"],
        [
            document("doc-1", "Identity proof"),
            document("doc-2", "Income certificate"),
        ],
    )

    assert result.status == ReadinessStatus.READY
    assert result.missing_documents == []
    assert result.authenticity_verified is False


def test_missing_required_document_needs_attention():
    result = assess_application_readiness(
        ["Identity proof", "Income certificate"],
        [document("doc-1", "Identity proof")],
    )

    assert result.status == ReadinessStatus.NEEDS_ATTENTION
    assert result.missing_documents == ["Income certificate"]


def test_document_type_matching_ignores_case_and_outer_spaces():
    result = assess_application_readiness(
        ["Identity proof"],
        [document("doc-1", "  IDENTITY PROOF ")],
    )

    assert result.status == ReadinessStatus.READY


def test_missing_requirements_return_insufficient_evidence():
    result = assess_application_readiness(
        None,
        [document("doc-1", "Identity proof")],
    )

    assert result.status == ReadinessStatus.INSUFFICIENT_EVIDENCE


def test_empty_requirements_are_not_assumed_to_mean_no_documents_needed():
    result = assess_application_readiness(
        [],
        [],
    )

    assert result.status == ReadinessStatus.INSUFFICIENT_EVIDENCE


def test_unrecognized_requirement_format_is_not_guessed():
    result = assess_application_readiness(
        {"identity": True},
        [],
    )

    assert result.status == ReadinessStatus.INSUFFICIENT_EVIDENCE


def test_invalid_requirement_entry_returns_insufficient_evidence():
    result = assess_application_readiness(
        ["Identity proof", ""],
        [],
    )

    assert result.status == ReadinessStatus.INSUFFICIENT_EVIDENCE


def test_duplicate_requirement_types_are_deduplicated():
    result = assess_application_readiness(
        ["Identity proof", " identity proof "],
        [document("doc-1", "Identity proof")],
    )

    assert result.status == ReadinessStatus.READY
    assert result.required_documents == ["Identity proof"]
