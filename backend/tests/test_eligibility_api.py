from fastapi.testclient import TestClient

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

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
