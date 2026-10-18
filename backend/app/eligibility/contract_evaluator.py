
"""Evaluate eligibility criteria using all/any contract logic."""

from app.eligibility.engine import evaluate_eligibility
from app.eligibility.models import (
    ConditionStatus,
    EligibilityResult,
    EligibilityStatus,
    SchemeRuleSet,
)


def evaluate_contract(
    scheme: SchemeRuleSet,
    profile: dict,
) -> EligibilityResult:
    """Evaluate a reviewed scheme and aggregate its criteria."""

    # Never infer eligibility from unreviewed rules.
    if not scheme.reviewed:
        return evaluate_eligibility(scheme, profile)

    if scheme.logic not in {"all", "any"}:
        raise ValueError("logic must be 'all' or 'any'")

    result = evaluate_eligibility(scheme, profile)
    conditions = result.conditions

    if scheme.logic == "all":
        required_conditions = [
            condition
            for rule, condition in zip(scheme.rules, conditions)
            if rule.required
        ]

        if any(c.status == ConditionStatus.FAIL for c in required_conditions):
            status = EligibilityStatus.NOT_ELIGIBLE
            summary = "One or more required criteria were not met."
        elif any(
            c.status in {
                ConditionStatus.MISSING,
                ConditionStatus.CONFLICT,
                ConditionStatus.UNSUPPORTED,
            }
            for c in required_conditions
        ):
            status = EligibilityStatus.INSUFFICIENT_INFORMATION
            summary = "More information is needed to assess eligibility."
        else:
            status = EligibilityStatus.ELIGIBLE
            summary = "All required criteria were met."

    else:  # any: each rule represents an alternative
        if any(c.status == ConditionStatus.PASS for c in conditions):
            status = EligibilityStatus.ELIGIBLE
            summary = "At least one eligibility alternative was met."
        elif any(
            c.status in {
                ConditionStatus.MISSING,
                ConditionStatus.CONFLICT,
                ConditionStatus.UNSUPPORTED,
            }
            for c in conditions
        ):
            status = EligibilityStatus.INSUFFICIENT_INFORMATION
            summary = "At least one eligibility alternative remains unresolved."
        else:
            status = EligibilityStatus.NOT_ELIGIBLE
            summary = "None of the eligibility alternatives were met."

    return EligibilityResult(
        scheme_id=result.scheme_id,
        scheme_name=result.scheme_name,
        rule_version=result.rule_version,
        status=status,
        summary=summary,
        reviewed=result.reviewed,
        conditions=result.conditions,
    )
