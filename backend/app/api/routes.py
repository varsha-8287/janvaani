from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database.session import get_db
from app.eligibility.engine import evaluate_eligibility
from app.eligibility.models import Rule, SchemeRuleSet
from app.eligibility.contract_evaluator import evaluate_contract
from app.eligibility.repository import (
    load_reviewed_scheme,
    SchemeNotFoundError,
    ReviewRequiredError,
)

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

class ProductionEligibilityRequest(BaseModel):
    scheme_id: str = Field(min_length=1)
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


@router.post("/eligibility/evaluate-reviewed")
def evaluate_reviewed(
    request: ProductionEligibilityRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Evaluate using approved criteria and verified database sources."""
    try:
        scheme, version, logic, rules = load_reviewed_scheme(
            db,
            request.scheme_id,
        )

        rule_set = SchemeRuleSet(
            scheme_id=str(scheme.id),
            scheme_name=scheme.title,
            version=str(version.version_number),
            rules=rules,
            reviewed=True,
            logic=logic,
        )

        result = evaluate_contract(rule_set, request.profile)
        response = result.to_dict()
        response["logic"] = logic
        response["criteria_schema_version"] = (
            version.eligibility_criteria["schema_version"]
        )
        response["review_status"] = version.review_status
        response["reason_code"] = result.status.value.lower()
        return response

    except SchemeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReviewRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc