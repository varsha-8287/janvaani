from fastapi.testclient import TestClient

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch

from app.main import app
from app.database.session import get_db
from app.eligibility.repository import (
    SchemeNotFoundError,
    ReviewRequiredError,
)

from types import SimpleNamespace


from app.eligibility.models import (
    ConditionResult,
    ConditionStatus,
    EligibilityResult,
    EligibilityStatus,
    Rule,
)


client = TestClient(app)

def make_request():
    return {
        "scheme_id": "test-scheme",
        "scheme_name": "Test Scheme",
        "rule_version": "1.0",
        "rules": [
            {
                "rule_id": "age-min",
                "field": "age",
                "operator": "gte",
                "expected": 18,
                "explanation": "Applicant must be at least 18.",
                "supported": True,
                "required": True,
            }
        ],
        "profile": {"age": 25},
    }


def test_valid_request_returns_200():
    response = client.post(
        "/api/eligibility/evaluate",
        json=make_request(),
    )

    assert response.status_code == 200
    assert response.json()["reviewed"] is False
    assert response.json()["status"] == "INSUFFICIENT_INFORMATION"


def test_empty_scheme_id_is_rejected():
    payload = make_request()
    payload["scheme_id"] = ""

    response = client.post(
        "/api/eligibility/evaluate",
        json=payload,
    )

    assert response.status_code == 422


def test_empty_rules_are_rejected():
    payload = make_request()
    payload["rules"] = []

    response = client.post(
        "/api/eligibility/evaluate",
        json=payload,
    )

    assert response.status_code == 422


def test_missing_profile_is_rejected():
    payload = make_request()
    del payload["profile"]

    response = client.post(
        "/api/eligibility/evaluate",
        json=payload,
    )

    assert response.status_code == 422


def test_health_endpoint_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"



def test_reviewed_endpoint_returns_404_for_missing_scheme():
    def fake_load(db, scheme_id):
        raise SchemeNotFoundError("Scheme not found")

    with patch(
        "app.api.routes.load_reviewed_scheme",
        side_effect=fake_load,
    ):
        response = client.post(
            "/api/eligibility/evaluate-reviewed",
            json={"scheme_id": "missing-scheme", "profile": {}},
        )

    assert response.status_code == 404


def test_reviewed_endpoint_returns_409_when_review_is_required():
    def fake_load(db, scheme_id):
        raise ReviewRequiredError("Scheme requires review")

    with patch(
        "app.api.routes.load_reviewed_scheme",
        side_effect=fake_load,
    ):
        response = client.post(
            "/api/eligibility/evaluate-reviewed",
            json={"scheme_id": "test-scheme", "profile": {}},
        )

    assert response.status_code == 409


def test_reviewed_endpoint_rejects_request_without_scheme_id():
    response = client.post(
        "/api/eligibility/evaluate-reviewed",
        json={"profile": {}},
    )

    assert response.status_code == 422


def test_reviewed_endpoint_returns_contract_metadata():
    fake_scheme = SimpleNamespace(
        id="test-scheme-id",
        title="Test Scheme",
    )
    fake_version = SimpleNamespace(
        version_number=1,
        eligibility_criteria={"schema_version": 1},
        review_status="approved",
    )
    fake_rule = Rule(
        rule_id="age",
        field="age",
        operator="gte",
        expected=18,
        explanation="Applicant must be at least 18.",
    )

    def fake_load(db, scheme_id):
        return fake_scheme, fake_version, "all", (fake_rule,)

    with (
        patch(
            "app.api.routes.load_reviewed_scheme",
            side_effect=fake_load,
        ),
        patch("app.api.routes.evaluate_contract") as mock_evaluate,
        patch(
            "app.api.routes.generate_eligibility_explanation",
            return_value={
                "explanation": "Your age meets the reviewed requirement.",
                "generated_by": "gemini",
                "source_references_included": False,
            },
        ) as mock_explanation,
    ):

        mock_evaluate.return_value = EligibilityResult(
            scheme_id="test-scheme-id",
            scheme_name="Test Scheme",
            rule_version="1",
            status=EligibilityStatus.ELIGIBLE,
            summary="All required criteria were met.",
            reviewed=True,
            conditions=(
                ConditionResult(
                    rule_id="age",
                    field="age",
                    status=ConditionStatus.PASS,
                    required=True,
                    explanation="Applicant must be at least 18.",
                    actual_value=25,
                    expected_value=18,
                ),
            ),
        )

        response = client.post(
            "/api/eligibility/evaluate-reviewed",
            json={
                "scheme_id": "test-scheme-id",
                "profile": {"age": 25},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["logic"] == "all"
    assert body["criteria_schema_version"] == 1
    assert body["review_status"] == "approved"
    assert body["status"] == "ELIGIBLE"
    assert body["explanation"] == (
        "Your age meets the reviewed requirement."
    )
    assert body["explanation_generated_by"] == "gemini"
    assert body["source_references_included"] is False
    mock_explanation.assert_called_once()

def test_reviewed_endpoint_returns_eligibility_when_gemini_fails():
    fake_scheme = SimpleNamespace(
        id="test-scheme-id",
        title="Test Scheme",
    )
    fake_version = SimpleNamespace(
        version_number=1,
        eligibility_criteria={"schema_version": 1},
        review_status="approved",
    )
    fake_rule = Rule(
        rule_id="age",
        field="age",
        operator="gte",
        expected=18,
        explanation="Applicant must be at least 18.",
    )

    def fake_load(db, scheme_id):
        return fake_scheme, fake_version, "all", (fake_rule,)

    with (
        patch(
            "app.api.routes.load_reviewed_scheme",
            side_effect=fake_load,
        ),
        patch("app.api.routes.evaluate_contract") as mock_evaluate,
        patch(
            "app.api.routes.generate_eligibility_explanation",
            return_value={
                "explanation": (
                    "The reviewed eligibility checks indicate that "
                    "you may qualify. Confirm the details with the "
                    "official scheme authority."
                ),
                "generated_by": "fallback",
                "source_references_included": False,
            },
        ) as mock_explanation,
    ):
        mock_evaluate.return_value = EligibilityResult(
            scheme_id="test-scheme-id",
            scheme_name="Test Scheme",
            rule_version="1",
            status=EligibilityStatus.ELIGIBLE,
            summary="All required criteria were met.",
            reviewed=True,
            conditions=(
                ConditionResult(
                    rule_id="age",
                    field="age",
                    status=ConditionStatus.PASS,
                    required=True,
                    explanation="Applicant must be at least 18.",
                    actual_value=25,
                    expected_value=18,
                ),
            ),
        )

        response = client.post(
            "/api/eligibility/evaluate-reviewed",
            json={
                "scheme_id": "test-scheme-id",
                "profile": {"age": 25},
            },
        )

    assert response.status_code == 200
    body = response.json()

    # The original deterministic decision must remain unchanged.
    assert body["status"] == "ELIGIBLE"
    assert body["reason_code"] == "eligible"

    # The endpoint should still return an explanation.
    assert body["explanation_generated_by"] == "fallback"
    assert "may qualify" in body["explanation"]
    mock_explanation.assert_called_once()
