
import pytest

from backend.app.eligibility.contract import (
    CriteriaValidationError,
    parse_criteria,
)


def valid_criteria():
    return {
        "schema_version": 1,
        "logic": "all",
        "rules": [
            {
                "rule_id": "minimum-age",
                "profile_field": "age",
                "operator": "gte",
                "expected_value": 18,
                "explanation": "Applicant must be at least 18.",
                "required": True,
                "source": {
                    "source_document_id": "source-001",
                    "source_url": "https://example.gov.in/scheme",
                    "reference": "Eligibility section",
                    "retrieved_at": "2026-10-18T10:00:00+00:00",
                },
            }
        ],
    }


def test_valid_criteria_is_parsed():
    logic, rules = parse_criteria(valid_criteria())

    assert logic == "all"
    assert len(rules) == 1
    assert rules[0].rule_id == "minimum-age"
    assert rules[0].field == "age"
    assert rules[0].operator == "gte"
    assert rules[0].expected == 18
    assert rules[0].source is not None


def test_any_logic_is_accepted():
    criteria = valid_criteria()
    criteria["logic"] = "any"

    logic, _ = parse_criteria(criteria)

    assert logic == "any"


@pytest.mark.parametrize("logic", ["AND", "or", "", None])
def test_invalid_logic_is_rejected(logic):
    criteria = valid_criteria()
    criteria["logic"] = logic

    with pytest.raises(CriteriaValidationError):
        parse_criteria(criteria)


def test_unknown_schema_version_is_rejected():
    criteria = valid_criteria()
    criteria["schema_version"] = 2

    with pytest.raises(CriteriaValidationError):
        parse_criteria(criteria)


def test_unknown_operator_is_rejected():
    criteria = valid_criteria()
    criteria["rules"][0]["operator"] = "approximately"

    with pytest.raises(CriteriaValidationError):
        parse_criteria(criteria)


def test_missing_source_is_rejected():
    criteria = valid_criteria()
    del criteria["rules"][0]["source"]

    with pytest.raises(CriteriaValidationError):
        parse_criteria(criteria)


def test_invalid_source_url_is_rejected():
    criteria = valid_criteria()
    criteria["rules"][0]["source"]["source_url"] = "not-a-url"

    with pytest.raises(CriteriaValidationError):
        parse_criteria(criteria)


def test_duplicate_rule_ids_are_rejected():
    criteria = valid_criteria()
    duplicate = dict(criteria["rules"][0])
    criteria["rules"].append(duplicate)

    with pytest.raises(CriteriaValidationError):
        parse_criteria(criteria)


def test_required_must_be_boolean():
    criteria = valid_criteria()
    criteria["rules"][0]["required"] = "yes"

    with pytest.raises(CriteriaValidationError):
        parse_criteria(criteria)
