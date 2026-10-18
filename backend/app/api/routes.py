
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.database.models import Scheme
from app.eligibility.engine import evaluate_eligibility
from app.eligibility.models import Rule, SchemeRuleSet
from app.eligibility.contract_evaluator import evaluate_contract
from app.eligibility.repository import (
    load_reviewed_scheme,
    SchemeNotFoundError,
    ReviewRequiredError,
)
from app.services.explanation_service import (
    generate_eligibility_explanation,
)


# Scheme catalogue endpoints
router = APIRouter(prefix="/schemes", tags=["Schemes"])

# Eligibility endpoints
eligibility_router = APIRouter(
    prefix="/api",
    tags=["Eligibility"],
)


@router.get("")
def list_schemes(
    government_level: str | None = Query(
        default=None,
        description="Filter by central, state, local, or other",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List published schemes that have an approved version."""
    stmt = (
        select(Scheme)
        .options(selectinload(Scheme.versions))
        .where(Scheme.status == "published")
        .where(Scheme.versions.any(review_status="approved"))
    )

    if government_level:
        allowed_levels = {"central", "state", "local", "other"}
        if government_level not in allowed_levels:
            raise HTTPException(
                status_code=422,
                detail="Invalid government_level",
            )
        stmt = stmt.where(Scheme.government_level == government_level)

    stmt = stmt.order_by(Scheme.title).offset(offset).limit(limit)
    schemes = db.scalars(stmt).all()

    return [
        {
            "slug": scheme.slug,
            "title": scheme.title,
            "administering_authority": scheme.administering_authority,
            "government_level": scheme.government_level,
            "versions": [
                {
                    "version_number": version.version_number,
                    "language": version.language,
                    "description": version.description,
                }
                for version in scheme.versions
                if version.review_status == "approved"
            ],
        }
        for scheme in schemes
    ]


@router.get("/{slug}")
def get_scheme(
    slug: str,
    db: Session = Depends(get_db),
):
    """Get a published scheme and its approved versions."""
    stmt = (
        select(Scheme)
        .options(selectinload(Scheme.versions))
        .where(Scheme.slug == slug)
        .where(Scheme.status == "published")
        .where(Scheme.versions.any(review_status="approved"))
    )
    scheme = db.scalars(stmt).first()

    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")

    approved_versions = [
        {
            "version_number": version.version_number,
            "language": version.language,
            "description": version.description,
            "benefits": version.benefits,
            "eligibility_criteria": version.eligibility_criteria,
            "required_documents": version.required_documents,
            "application_process": version.application_process,
            "valid_from": version.valid_from,
            "valid_until": version.valid_until,
        }
        for version in scheme.versions
        if version.review_status == "approved"
    ]

    return {
        "slug": scheme.slug,
        "title": scheme.title,
        "administering_authority": scheme.administering_authority,
        "government_level": scheme.government_level,
        "versions": approved_versions,
    }


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


@eligibility_router.post("/eligibility/evaluate")
def evaluate(request: EligibilityRequest) -> dict[str, Any]:
    """Development endpoint. Client-supplied rules are not trusted as reviewed."""
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
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@eligibility_router.post("/eligibility/evaluate-reviewed")
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

        explanation_result = generate_eligibility_explanation(
            response,
            evidence=response["conditions"],
        )

        response["explanation"] = explanation_result["explanation"]
        response["explanation_generated_by"] = (
            explanation_result["generated_by"]
        )
        response["source_references_included"] = (
            explanation_result["source_references_included"]
        )

        return response

    except SchemeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReviewRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
