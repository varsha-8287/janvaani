
from app.services.explanation_service import (
    generate_eligibility_explanation,
)

from types import SimpleNamespace

from app.services import explanation_service

def test_missing_api_key_uses_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = generate_eligibility_explanation(
        {
            "status": "INSUFFICIENT_INFORMATION",
            "summary": "More information is needed.",
            "conditions": [
                {
                    "field": "income",
                    "status": "MISSING",
                    "required": True,
                    "explanation": "Income information is missing.",
                    "source": None,
                }
            ],
        }
    )

    assert result["generated_by"] == "fallback"
    assert "cannot be determined" in result["explanation"].lower()
    assert result["source_references_included"] is False


def test_empty_conditions_use_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    result = generate_eligibility_explanation(
        {
            "status": "INSUFFICIENT_INFORMATION",
            "summary": "More information is needed.",
            "conditions": [],
        }
    )

    assert result["generated_by"] == "fallback"
    assert result["source_references_included"] is False


def test_fallback_preserves_not_eligible_result(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = generate_eligibility_explanation(
        {
            "status": "NOT_ELIGIBLE",
            "summary": "At least one required condition was not satisfied.",
            "conditions": [
                {
                    "field": "age",
                    "status": "FAIL",
                    "required": True,
                    "explanation": "The required age condition was not met.",
                    "source": None,
                }
            ],
        }
    )

    assert result["generated_by"] == "fallback"
    assert "not met" in result["explanation"].lower()

def test_gemini_success_uses_safe_context(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    captured = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured["prompt"] = kwargs["contents"]
            return SimpleNamespace(
                text="Your eligibility needs further review."
            )

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-key"
            self.models = FakeModels()

    monkeypatch.setattr(
        explanation_service.genai, "Client", FakeClient
    )

    result = explanation_service.generate_eligibility_explanation(
        {
            "status": "INSUFFICIENT_INFORMATION",
            "summary": "More information is needed.",
            "scheme_name": "Example scheme",
            "rule_version": "1",
            "reviewed": True,
            "conditions": [
                {
                    "field": "income",
                    "status": "MISSING",
                    "required": True,
                    "explanation": "Income information is missing.",
                    "actual_value": "PRIVATE_PROFILE_VALUE",
                    "expected_value": 10000,
                    "source": None,
                }
            ],
        }
    )

    assert result["generated_by"] == "gemini"
    assert result["explanation"] == (
        "Your eligibility needs further review."
    )
    assert "PRIVATE_PROFILE_VALUE" not in captured["prompt"]


def test_gemini_failure_uses_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeClient:
        def __init__(self, api_key):
            self.models = self

        def generate_content(self, **kwargs):
            raise RuntimeError("Simulated Gemini outage")

    monkeypatch.setattr(
        explanation_service.genai, "Client", FakeClient
    )

    result = explanation_service.generate_eligibility_explanation(
        {
            "status": "NOT_ELIGIBLE",
            "summary": "A required condition was not satisfied.",
            "conditions": [
                {
                    "field": "age",
                    "status": "FAIL",
                    "required": True,
                    "explanation": "The age condition was not met.",
                    "source": None,
                }
            ],
        }
    )

    assert result["generated_by"] == "fallback"
    assert "not met" in result["explanation"].lower()

