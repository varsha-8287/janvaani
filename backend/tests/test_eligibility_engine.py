from backend.app.eligibility.engine import evaluate_eligibility
from backend.app.eligibility.models import (
    ConditionStatus,
    EligibilityStatus,
    Rule,
    SchemeRuleSet,
    SourceReference,
)


def reviewed_scheme(*rules):
    return SchemeRuleSet(
        scheme_id="example-only",
        scheme_name="Example scheme (test fixture only)",
        version="test-v1",
        rules=rules,
        reviewed=True,
    )


def test_all_required_conditions_pass():
    scheme = reviewed_scheme(
        Rule("r1", "age", "gte", 18, "Age threshold in test fixture."),
        Rule("r2", "state", "in", ["TN", "KA"], "State list in test fixture."),
    )
    result = evaluate_eligibility(scheme, {"age": 25, "state": "TN"})
    assert result.status == EligibilityStatus.ELIGIBLE
    assert [c.status for c in result.conditions] == [ConditionStatus.PASS, ConditionStatus.PASS]


def test_required_failure_means_not_eligible():
    result = evaluate_eligibility(
        reviewed_scheme(Rule("r1", "age", "gte", 18)),
        {"age": 16},
    )
    assert result.status == EligibilityStatus.NOT_ELIGIBLE
    assert result.conditions[0].status == ConditionStatus.FAIL


def test_missing_required_field_means_insufficient_information():
    result = evaluate_eligibility(
        reviewed_scheme(Rule("r1", "land_acres", "lte", 5)),
        {},
    )
    assert result.status == EligibilityStatus.INSUFFICIENT_INFORMATION
    assert result.conditions[0].status == ConditionStatus.MISSING


def test_unreviewed_scheme_never_returns_eligible():
    scheme = SchemeRuleSet("x", "Unreviewed test fixture", "v1", (Rule("r1", "age", "gte", 18),), reviewed=False)
    result = evaluate_eligibility(scheme, {"age": 30})
    assert result.status == EligibilityStatus.INSUFFICIENT_INFORMATION


def test_unsupported_rule_is_not_guessed():
    scheme = reviewed_scheme(Rule("r1", "category", "fuzzy_guess", "farmer", supported=True))
    result = evaluate_eligibility(scheme, {"category": "farmer"})
    assert result.status == EligibilityStatus.INSUFFICIENT_INFORMATION
    assert result.conditions[0].status == ConditionStatus.UNSUPPORTED


def test_type_mismatch_is_conflict_not_crash():
    result = evaluate_eligibility(
        reviewed_scheme(Rule("r1", "age", "gte", 18)),
        {"age": "not-a-number"},
    )
    assert result.status == EligibilityStatus.INSUFFICIENT_INFORMATION
    assert result.conditions[0].status == ConditionStatus.CONFLICT


def test_optional_failure_does_not_block_but_is_reported():
    scheme = reviewed_scheme(
        Rule("r1", "age", "gte", 18),
        Rule("r2", "district", "eq", "A", required=False),
    )
    result = evaluate_eligibility(scheme, {"age": 22, "district": "B"})
    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.conditions[1].status == ConditionStatus.FAIL


def test_source_provenance_is_serialized():
    source = SourceReference(
        source_title="Test fixture source",
        source_url="https://example.invalid/test",
        retrieved_on="2026-10-15",
        rule_version="test-v1",
    )
    result = evaluate_eligibility(
        reviewed_scheme(Rule("r1", "age", "gte", 18, source=source)),
        {"age": 21},
    ).to_dict()
    assert result["conditions"][0]["source"]["source_url"] == "https://example.invalid/test"
