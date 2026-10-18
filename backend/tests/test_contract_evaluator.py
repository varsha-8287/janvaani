
import pytest

from app.eligibility.contract_evaluator import evaluate_contract
from app.eligibility.models import (
    ConditionStatus,
    EligibilityStatus,
    Rule,
    SchemeRuleSet,
)


def make_scheme(logic="all", rules=None, reviewed=True):
    if rules is None:
        rules = (
            Rule(
                rule_id="age",
                field="age",
                operator="gte",
                expected=18,
                explanation="Applicant must be at least 18.",
                required=True,
            ),
        )

    return SchemeRuleSet(
        scheme_id="test-scheme",
        scheme_name="Test Scheme",
        version="1",
        rules=rules,
        reviewed=reviewed,
        logic=logic,
    )


def test_all_pass_returns_eligible():
    result = evaluate_contract(make_scheme(), {"age": 25})
    assert result.status == EligibilityStatus.ELIGIBLE


def test_all_required_failure_returns_not_eligible():
    result = evaluate_contract(make_scheme(), {"age": 16})
    assert result.status == EligibilityStatus.NOT_ELIGIBLE


def test_all_missing_required_field_returns_insufficient_information():
    result = evaluate_contract(make_scheme(), {})
    assert result.status == EligibilityStatus.INSUFFICIENT_INFORMATION


def test_any_pass_returns_eligible():
    rules = (
        Rule("age", "age", "gte", 18),
        Rule("residence", "state", "eq", "Tamil Nadu"),
    )
    result = evaluate_contract(
        make_scheme(logic="any", rules=rules),
        {"age": 20},
    )
    assert result.status == EligibilityStatus.ELIGIBLE


def test_any_unresolved_alternative_returns_insufficient_information():
    rules = (
        Rule("age", "age", "gte", 18),
        Rule("residence", "state", "eq", "Tamil Nadu"),
    )
    result = evaluate_contract(
        make_scheme(logic="any", rules=rules),
        {"age": 16},
    )
    assert result.status == EligibilityStatus.INSUFFICIENT_INFORMATION


def test_any_all_failed_returns_not_eligible():
    rules = (
        Rule("age", "age", "gte", 18),
        Rule("residence", "state", "eq", "Tamil Nadu"),
    )
    result = evaluate_contract(
        make_scheme(logic="any", rules=rules),
        {"age": 16, "state": "Kerala"},
    )
    assert result.status == EligibilityStatus.NOT_ELIGIBLE


def test_unreviewed_scheme_never_claims_eligibility():
    result = evaluate_contract(
        make_scheme(reviewed=False),
        {"age": 25},
    )
    assert result.status == EligibilityStatus.INSUFFICIENT_INFORMATION
    assert result.reviewed is False
