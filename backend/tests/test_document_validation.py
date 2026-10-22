
from app.documents.schemas import ExtractedDocument
from app.documents.validation import (
    detect_profile_conflicts,
    validate_document,
)


def test_missing_required_field_is_reported_without_inventing_value():
    document = ExtractedDocument(
        document_id="doc-1",
        document_type="income_certificate",
        fields={"annual_income": 120000},
    )

    result = validate_document(
        document,
        required_fields={"annual_income", "issue_date"},
    )

    assert result.valid is False
    assert [(i.field_name, i.status) for i in result.issues] == [
        ("issue_date", "MISSING")
    ]
    assert result.authenticity_verified is False


def test_invalid_income_is_reported():
    document = ExtractedDocument(
        document_id="doc-2",
        document_type="income_certificate",
        fields={"annual_income": -500},
    )

    result = validate_document(document)

    assert result.valid is False
    assert result.issues[0].field_name == "annual_income"
    assert result.issues[0].status == "INVALID"
    assert result.issues[0].evidence[0].document_id == "doc-2"


def test_conflicting_profile_value_is_reported_not_overwritten():
    document = ExtractedDocument(
        document_id="doc-3",
        document_type="identity_proof",
        fields={"name": "Ananya"},
    )

    issues = detect_profile_conflicts(
        document,
        {"name": "Ananya Sharma"},
        comparable_fields={"name"},
    )

    assert len(issues) == 1
    assert issues[0].status == "CONFLICT"
    assert "neither value was chosen" in issues[0].explanation


def test_equal_values_do_not_create_conflict():
    document = ExtractedDocument(
        document_id="doc-4",
        document_type="identity_proof",
        fields={"name": "Ananya"},
    )

    issues = detect_profile_conflicts(
        document,
        {"name": "Ananya"},
        comparable_fields={"name"},
    )

    assert issues == []


def test_missing_profile_value_is_not_treated_as_conflict():
    document = ExtractedDocument(
        document_id="doc-5",
        document_type="identity_proof",
        fields={"name": "Ananya"},
    )

    issues = detect_profile_conflicts(
        document,
        {},
        comparable_fields={"name"},
    )

    assert issues == []


def test_unknown_field_format_is_not_guessed():
    document = ExtractedDocument(
        document_id="doc-6",
        document_type="unknown_document",
        fields={"some_field": "some value"},
    )

    result = validate_document(document)

    assert result.valid is True
    assert result.issues == []
    assert result.authenticity_verified is False
