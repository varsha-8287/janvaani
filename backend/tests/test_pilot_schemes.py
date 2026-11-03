"""Tests for Janvaani Phase 3B Eight-Scheme Verification Pilot Records.

Validates that:
1. All 8 proposed pilot records match the JSON schema and preserve dataset IDs.
2. The formal eligibility criteria blocks parse cleanly via contract v1 parser.
3. The deterministic eligibility engine evaluates sample citizen profiles accurately.
4. Incomplete profiles safely yield INSUFFICIENT_INFORMATION without false positives.
5. Invariants (unreviewed safety policy, no database writes) hold.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.eligibility.contract import parse_criteria
from app.eligibility.contract_evaluator import evaluate_contract
from app.eligibility.models import (
    EligibilityStatus,
    SchemeRuleSet,
)
from app.ingestion.schemas import SchemeIngestionInput

REPO_ROOT = Path(__file__).resolve().parents[2]
PILOT_DIR = REPO_ROOT / "janvaani_government_schemes_dataset" / "staging" / "pilot"

PILOT_SCHEME_METADATA = {
    "pm-kisan": {
        "external_id": "62a70e86f038bd8499a6aa53",
        "level": "central",
        "expected_rules": 4,
    },
    "ab-pmjay": {
        "external_id": "62a0702feaca073ef50831fe",
        "level": "central",
        "expected_rules": 3,
    },
    "apy": {
        "external_id": "628b41a2c9b440ca7f31ff6c",
        "level": "central",
        "expected_rules": 4,
    },
    "ksy": {
        "external_id": "64806afd481f59106a67c9dd",
        "level": "state",
        "expected_rules": 4,
    },
    "ma": {
        "external_id": "6434724ebd37517394eb16f7",
        "level": "state",
        "expected_rules": 2,
    },
    "ignoapstn": {
        "external_id": "65e04974da55878ebe0900eb",
        "level": "state",
        "expected_rules": 4,
    },
    "hpms": {
        "external_id": "6786aa1c4bf34a9c20858c9a",
        "level": "state",
        "expected_rules": 5,
    },
    "dpmss": {
        "external_id": "649a8d82380f8e123543e9a2",
        "level": "state",
        "expected_rules": 4,
    },
}


def load_pilot_record(slug: str) -> dict:
    file_path = PILOT_DIR / f"{slug}.json"
    assert file_path.is_file(), f"Pilot file not found: {file_path}"
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("slug, meta", PILOT_SCHEME_METADATA.items())
def test_pilot_record_structure_and_provenance(slug: str, meta: dict):
    data = load_pilot_record(slug)
    assert data["slug"] == slug
    assert data["government_level"] == meta["level"]
    assert data["record_status"] == "pending_review"

    # External ID preserved
    ext_ids = {ext["namespace"]: ext["value"] for ext in data.get("external_ids", [])}
    assert ext_ids.get("kaggle_csv") == meta["external_id"]

    # Source records verified
    assert len(data["source_records"]) >= 1
    for src in data["source_records"]:
        assert src["url"].startswith("http")
        assert src["review_status"] == "verified"
        assert src["license_or_reuse_basis"]


@pytest.mark.parametrize("slug, meta", PILOT_SCHEME_METADATA.items())
def test_pilot_criteria_parses_cleanly(slug: str, meta: dict):
    data = load_pilot_record(slug)
    criteria = data["eligibility"]
    logic, rules = parse_criteria(criteria)

    assert logic in {"all", "any"}
    assert len(rules) == meta["expected_rules"]
    for rule in rules:
        assert rule.rule_id
        assert rule.field
        assert rule.operator in {"eq", "neq", "in", "not_in", "gte", "gt", "lte", "lt", "exists"}
        assert rule.source is not None


@pytest.mark.parametrize("slug", PILOT_SCHEME_METADATA.keys())
def test_pilot_record_maps_to_ingestion_input(slug: str):
    data = load_pilot_record(slug)
    src = data["source_records"][0]
    payload = {
        "slug": data["slug"],
        "title": data["title"],
        "administering_authority": data.get("administering_authority"),
        "government_level": data["government_level"],
        "language": data.get("language", "en"),
        "description": data.get("summary"),
        "benefits": data.get("benefits"),
        "eligibility_criteria": data.get("eligibility"),
        "required_documents": data.get("required_documents"),
        "application_process": data.get("application_steps"),
        "valid_from": data.get("valid_from"),
        "valid_until": data.get("valid_until"),
        "source_url": src["url"],
        "publisher": src.get("publisher"),
        "retrieved_at": src["retrieved_at"],
        "content_hash": src.get("content_hash"),
    }
    ingestion_model = SchemeIngestionInput(**payload)
    assert ingestion_model.slug == data["slug"]
    assert ingestion_model.title == data["title"]
    assert ingestion_model.source_url == src["url"]


def test_pm_kisan_evaluation():
    data = load_pilot_record("pm-kisan")
    logic, rules = parse_criteria(data["eligibility"])
    scheme_rule_set = SchemeRuleSet(
        scheme_id=data["slug"],
        scheme_name=data["title"],
        version="pilot-v1",
        reviewed=True,
        logic=logic,
        rules=rules,
    )

    # 1. Eligible farmer
    profile_eligible = {
        "is_landholding_farmer": True,
        "is_income_tax_payer": False,
        "is_institutional_landholder": False,
        "is_serving_or_retired_govt_employee": False,
    }
    res = evaluate_contract(scheme_rule_set, profile_eligible)
    assert res.status == EligibilityStatus.ELIGIBLE

    # 2. Excluded: income tax payer
    profile_taxpayer = {
        "is_landholding_farmer": True,
        "is_income_tax_payer": True,
        "is_institutional_landholder": False,
        "is_serving_or_retired_govt_employee": False,
    }
    res_tax = evaluate_contract(scheme_rule_set, profile_taxpayer)
    assert res_tax.status == EligibilityStatus.NOT_ELIGIBLE

    # 3. Missing information: not enough info
    profile_incomplete = {"is_landholding_farmer": True}
    res_inc = evaluate_contract(scheme_rule_set, profile_incomplete)
    assert res_inc.status == EligibilityStatus.INSUFFICIENT_INFORMATION


def test_apy_evaluation():
    data = load_pilot_record("apy")
    logic, rules = parse_criteria(data["eligibility"])
    scheme_rule_set = SchemeRuleSet(
        scheme_id=data["slug"],
        scheme_name=data["title"],
        version="pilot-v1",
        reviewed=True,
        logic=logic,
        rules=rules,
    )

    # 1. Eligible 28-year-old non-taxpayer with bank account
    profile_eligible = {
        "age": 28,
        "is_income_tax_payer": False,
        "has_savings_bank_account": True,
    }
    assert evaluate_contract(scheme_rule_set, profile_eligible).status == EligibilityStatus.ELIGIBLE

    # 2. Ineligible: age 45 (> 40)
    profile_too_old = {
        "age": 45,
        "is_income_tax_payer": False,
        "has_savings_bank_account": True,
    }
    assert evaluate_contract(scheme_rule_set, profile_too_old).status == EligibilityStatus.NOT_ELIGIBLE

    # 3. Ineligible: tax payer exclusion
    profile_taxpayer = {
        "age": 30,
        "is_income_tax_payer": True,
        "has_savings_bank_account": True,
    }
    assert evaluate_contract(scheme_rule_set, profile_taxpayer).status == EligibilityStatus.NOT_ELIGIBLE


def test_ksy_evaluation():
    data = load_pilot_record("ksy")
    logic, rules = parse_criteria(data["eligibility"])
    scheme_rule_set = SchemeRuleSet(
        scheme_id=data["slug"],
        scheme_name=data["title"],
        version="pilot-v1",
        reviewed=True,
        logic=logic,
        rules=rules,
    )

    # 1. Eligible UP girl child, income <= 300000
    profile_eligible = {
        "state": "Uttar Pradesh",
        "annual_income": 200000,
        "gender": "female",
        "eligible_girls_in_family": 1,
    }
    assert evaluate_contract(scheme_rule_set, profile_eligible).status == EligibilityStatus.ELIGIBLE

    # 2. Ineligible: income 350000 (> 3 Lakh)
    profile_high_income = {
        "state": "Uttar Pradesh",
        "annual_income": 350000,
        "gender": "female",
        "eligible_girls_in_family": 1,
    }
    assert evaluate_contract(scheme_rule_set, profile_high_income).status == EligibilityStatus.NOT_ELIGIBLE

    # 3. Ineligible: different state
    profile_bihar = {
        "state": "Bihar",
        "annual_income": 150000,
        "gender": "female",
        "eligible_girls_in_family": 1,
    }
    assert evaluate_contract(scheme_rule_set, profile_bihar).status == EligibilityStatus.NOT_ELIGIBLE


def test_ab_pmjay_any_logic_evaluation():
    data = load_pilot_record("ab-pmjay")
    logic, rules = parse_criteria(data["eligibility"])
    assert logic == "any"
    scheme_rule_set = SchemeRuleSet(
        scheme_id=data["slug"],
        scheme_name=data["title"],
        version="pilot-v1",
        reviewed=True,
        logic=logic,
        rules=rules,
    )

    # 1. Eligible via senior citizen universal 70+ rule
    profile_senior = {"age": 72}
    assert evaluate_contract(scheme_rule_set, profile_senior).status == EligibilityStatus.ELIGIBLE

    # 2. Eligible via urban occupational category (street vendor)
    profile_urban = {"age": 35, "urban_occupational_category": "street_vendor"}
    assert evaluate_contract(scheme_rule_set, profile_urban).status == EligibilityStatus.ELIGIBLE

    # 3. Eligible via rural SECC deprivation (d1_one_room_kucha)
    profile_rural = {"age": 40, "secc_deprivation_category": "d1_one_room_kucha"}
    assert evaluate_contract(scheme_rule_set, profile_rural).status == EligibilityStatus.ELIGIBLE

    # 4. Incomplete profile with age under 70 and no categories specified
    profile_unknown = {"age": 45}
    assert evaluate_contract(scheme_rule_set, profile_unknown).status == EligibilityStatus.INSUFFICIENT_INFORMATION


def test_unreviewed_safety_policy():
    """Unreviewed scheme rules must NEVER return ELIGIBLE status."""
    data = load_pilot_record("pm-kisan")
    logic, rules = parse_criteria(data["eligibility"])
    unreviewed_set = SchemeRuleSet(
        scheme_id=data["slug"],
        scheme_name=data["title"],
        version="pilot-v1",
        reviewed=False,  # Still pending review
        logic=logic,
        rules=rules,
    )

    profile_eligible = {
        "is_landholding_farmer": True,
        "is_income_tax_payer": False,
        "is_institutional_landholder": False,
        "is_serving_or_retired_govt_employee": False,
    }
    result = evaluate_contract(unreviewed_set, profile_eligible)
    assert result.status == EligibilityStatus.INSUFFICIENT_INFORMATION
    assert "not been reviewed" in result.summary.lower()


def test_ma_evaluation():
    data = load_pilot_record("ma")
    logic, rules = parse_criteria(data["eligibility"])
    scheme_rule_set = SchemeRuleSet(
        scheme_id=data["slug"],
        scheme_name=data["title"],
        version="pilot-v1",
        reviewed=True,
        logic=logic,
        rules=rules,
    )

    # 1. Eligible Gujarat family with income <= 400000
    assert evaluate_contract(
        scheme_rule_set, {"state": "Gujarat", "annual_income": 250000}
    ).status == EligibilityStatus.ELIGIBLE

    # 2. Ineligible: income > 400000
    assert evaluate_contract(
        scheme_rule_set, {"state": "Gujarat", "annual_income": 450000}
    ).status == EligibilityStatus.NOT_ELIGIBLE

    # 3. Ineligible: outside Gujarat
    assert evaluate_contract(
        scheme_rule_set, {"state": "Maharashtra", "annual_income": 200000}
    ).status == EligibilityStatus.NOT_ELIGIBLE

    # 4. Incomplete: missing income
    assert evaluate_contract(
        scheme_rule_set, {"state": "Gujarat"}
    ).status == EligibilityStatus.INSUFFICIENT_INFORMATION


def test_ignoapstn_evaluation():
    data = load_pilot_record("ignoapstn")
    logic, rules = parse_criteria(data["eligibility"])
    scheme_rule_set = SchemeRuleSet(
        scheme_id=data["slug"],
        scheme_name=data["title"],
        version="pilot-v1",
        reviewed=True,
        logic=logic,
        rules=rules,
    )

    # 1. Eligible destitute senior citizen in Tamil Nadu
    profile_eligible = {
        "state": "Tamil Nadu",
        "age": 65,
        "is_bpl": True,
        "is_destitute": True,
    }
    assert evaluate_contract(scheme_rule_set, profile_eligible).status == EligibilityStatus.ELIGIBLE

    # 2. Ineligible: under 60
    profile_underage = {
        "state": "Tamil Nadu",
        "age": 58,
        "is_bpl": True,
        "is_destitute": True,
    }
    assert evaluate_contract(scheme_rule_set, profile_underage).status == EligibilityStatus.NOT_ELIGIBLE

    # 3. Ineligible: not destitute
    profile_not_destitute = {
        "state": "Tamil Nadu",
        "age": 68,
        "is_bpl": True,
        "is_destitute": False,
    }
    assert evaluate_contract(scheme_rule_set, profile_not_destitute).status == EligibilityStatus.NOT_ELIGIBLE

    # 4. Incomplete: missing destitute flag
    profile_missing_destitute = {
        "state": "Tamil Nadu",
        "age": 68,
        "is_bpl": True,
    }
    assert evaluate_contract(scheme_rule_set, profile_missing_destitute).status == EligibilityStatus.INSUFFICIENT_INFORMATION


def test_hpms_evaluation():
    data = load_pilot_record("hpms")
    logic, rules = parse_criteria(data["eligibility"])
    scheme_rule_set = SchemeRuleSet(
        scheme_id=data["slug"],
        scheme_name=data["title"],
        version="pilot-v1",
        reviewed=True,
        logic=logic,
        rules=rules,
    )

    # 1. Eligible minority student in Haryana
    profile_eligible = {
        "state": "Haryana",
        "religion": "Muslim",
        "previous_examination_marks_percentage": 72,
        "annual_income": 150000,
        "education_level": "undergraduate",
    }
    assert evaluate_contract(scheme_rule_set, profile_eligible).status == EligibilityStatus.ELIGIBLE

    # 2. Ineligible: marks below 50%
    profile_low_marks = {
        "state": "Haryana",
        "religion": "Sikh",
        "previous_examination_marks_percentage": 48,
        "annual_income": 120000,
        "education_level": "undergraduate",
    }
    assert evaluate_contract(scheme_rule_set, profile_low_marks).status == EligibilityStatus.NOT_ELIGIBLE

    # 3. Ineligible: non-notified religion
    profile_non_minority = {
        "state": "Haryana",
        "religion": "Hindu",
        "previous_examination_marks_percentage": 75,
        "annual_income": 100000,
        "education_level": "undergraduate",
    }
    assert evaluate_contract(scheme_rule_set, profile_non_minority).status == EligibilityStatus.NOT_ELIGIBLE

    # 4. Ineligible: income > 200000
    profile_high_income = {
        "state": "Haryana",
        "religion": "Christian",
        "previous_examination_marks_percentage": 65,
        "annual_income": 250000,
        "education_level": "undergraduate",
    }
    assert evaluate_contract(scheme_rule_set, profile_high_income).status == EligibilityStatus.NOT_ELIGIBLE


def test_dpmss_evaluation():
    data = load_pilot_record("dpmss")
    logic, rules = parse_criteria(data["eligibility"])
    scheme_rule_set = SchemeRuleSet(
        scheme_id=data["slug"],
        scheme_name=data["title"],
        version="pilot-v1",
        reviewed=True,
        logic=logic,
        rules=rules,
    )

    # 1. Eligible Gurjar student in Rajasthan
    profile_eligible = {
        "state": "Rajasthan",
        "caste_category": "Gurjar",
        "annual_income": 200000,
        "education_level": "undergraduate",
    }
    assert evaluate_contract(scheme_rule_set, profile_eligible).status == EligibilityStatus.ELIGIBLE

    # 2. Ineligible: non-MBC caste
    profile_general = {
        "state": "Rajasthan",
        "caste_category": "General",
        "annual_income": 150000,
        "education_level": "undergraduate",
    }
    assert evaluate_contract(scheme_rule_set, profile_general).status == EligibilityStatus.NOT_ELIGIBLE

    # 3. Ineligible: income > 250000
    profile_high_income = {
        "state": "Rajasthan",
        "caste_category": "Banjara",
        "annual_income": 300000,
        "education_level": "undergraduate",
    }
    assert evaluate_contract(scheme_rule_set, profile_high_income).status == EligibilityStatus.NOT_ELIGIBLE


def test_contradictory_and_incompatible_profile_types():
    """Type conflicts and invalid types must safely yield INSUFFICIENT_INFORMATION, never crash or falsely approve."""
    # 1. APY with string age instead of int
    data_apy = load_pilot_record("apy")
    logic_apy, rules_apy = parse_criteria(data_apy["eligibility"])
    scheme_apy = SchemeRuleSet(
        scheme_id=data_apy["slug"],
        scheme_name=data_apy["title"],
        version="pilot-v1",
        reviewed=True,
        logic=logic_apy,
        rules=rules_apy,
    )
    profile_conflict_age = {
        "age": "thirty-two",  # String causes TypeError on >= comparison
        "is_income_tax_payer": False,
        "has_savings_bank_account": True,
    }
    res_conflict = evaluate_contract(scheme_apy, profile_conflict_age)
    assert res_conflict.status == EligibilityStatus.INSUFFICIENT_INFORMATION
    conflict_conditions = [c for c in res_conflict.conditions if c.field == "age"]
    assert any(c.status.value == "CONFLICT" for c in conflict_conditions)

    # 2. PM-KISAN with None and empty strings
    data_kisan = load_pilot_record("pm-kisan")
    logic_kisan, rules_kisan = parse_criteria(data_kisan["eligibility"])
    scheme_kisan = SchemeRuleSet(
        scheme_id=data_kisan["slug"],
        scheme_name=data_kisan["title"],
        version="pilot-v1",
        reviewed=True,
        logic=logic_kisan,
        rules=rules_kisan,
    )
    profile_empty = {
        "is_landholding_farmer": None,
        "is_income_tax_payer": "",
    }
    res_empty = evaluate_contract(scheme_kisan, profile_empty)
    assert res_empty.status == EligibilityStatus.INSUFFICIENT_INFORMATION


def test_pmjay_all_options_fail_yields_not_eligible():
    """In 'any' logic, when all alternatives are explicitly evaluated and FAIL, status is NOT_ELIGIBLE."""
    data = load_pilot_record("ab-pmjay")
    logic, rules = parse_criteria(data["eligibility"])
    assert logic == "any"
    scheme_rule_set = SchemeRuleSet(
        scheme_id=data["slug"],
        scheme_name=data["title"],
        version="pilot-v1",
        reviewed=True,
        logic=logic,
        rules=rules,
    )
    profile_ineligible = {
        "age": 40,  # Fails age >= 70
        "secc_deprivation_category": "none",  # Fails rural list
        "urban_occupational_category": "corporate_executive",  # Fails urban list
    }
    res = evaluate_contract(scheme_rule_set, profile_ineligible)
    assert res.status == EligibilityStatus.NOT_ELIGIBLE
    assert "None of the eligibility alternatives were met" in res.summary


def test_all_logic_fail_overrides_missing():
    """In 'all' logic, a definitive FAIL on any required rule causes NOT_ELIGIBLE even if another is MISSING."""
    data = load_pilot_record("apy")
    logic, rules = parse_criteria(data["eligibility"])
    scheme_rule_set = SchemeRuleSet(
        scheme_id=data["slug"],
        scheme_name=data["title"],
        version="pilot-v1",
        reviewed=True,
        logic=logic,
        rules=rules,
    )
    # Age 50 is definitely disqualified (> 40). Even if tax payer status is unknown (missing), status must be NOT_ELIGIBLE.
    profile_definitively_out = {"age": 50}
    res = evaluate_contract(scheme_rule_set, profile_definitively_out)
    assert res.status == EligibilityStatus.NOT_ELIGIBLE

