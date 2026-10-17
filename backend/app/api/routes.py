
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.eligibility.engine import evaluate_eligibility
from app.eligibility.models import Rule, SchemeRuleSet

router = APIRouter()


class RuleInput(BaseModel):
    rule_id: str
    field: str
    operator: str
    expected: Any = None
    explanation: str = ""
    supported: bool = True
    required: bool = True


class EligibilityRequest(BaseModel):
    scheme_id: str = Field(min_length=1)
    scheme_name: str = Field(min_length=1)
    rule_version: str = Field(min_length=1)
    rules: list[RuleInput] = Field(min_length=1)
    profile: dict[str, Any]


@router.post("/eligibility/evaluate")
def evaluate(request: EligibilityRequest) -> dict[str, Any]:
    """Development endpoint. Client-supplied rules are never trusted as reviewed."""
    try:
        rules = [
            Rule(
                rule_id=item.rule_id,
                field=item.field,
                operator=item.operator,
                expected=item.expected,
                explanation=item.explanation,
                supported=item.supported,
                required=item.required,
            )
            for item in request.rules
        ]

        scheme = SchemeRuleSet(
            scheme_id=request.scheme_id,
            scheme_name=request.scheme_name,
            version=request.rule_version,
            rules=rules,
            reviewed=False,
        )

        result = evaluate_eligibility(scheme, request.profile)
        return result.to_dict()

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
