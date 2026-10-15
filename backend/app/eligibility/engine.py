"""Deterministic, explainable eligibility evaluator. No LLM calls belong here."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import (
    ConditionResult,
    ConditionStatus,
    EligibilityResult,
    EligibilityStatus,
    Rule,
    SchemeRuleSet,
)


SUPPORTED_OPERATORS = {"eq", "neq", "in", "not_in", "gte", "gt", "lte", "lt", "exists"}


def _evaluate_rule(rule: Rule, profile: Mapping[str, Any]) -> ConditionResult:
    if not rule.supported or rule.operator not in SUPPORTED_OPERATORS:
        return ConditionResult(
            rule_id=rule.rule_id,
            field=rule.field,
            status=ConditionStatus.UNSUPPORTED,
            required=rule.required,
            explanation=rule.explanation or "This rule has not been verified for automated evaluation.",
            source=rule.source,
            expected_value=rule.expected,
        )

    if rule.operator == "exists":
        present = rule.field in profile and profile[rule.field] is not None
        return ConditionResult(
            rule_id=rule.rule_id,
            field=rule.field,
            status=ConditionStatus.PASS if present else ConditionStatus.MISSING,
            required=rule.required,
            explanation=rule.explanation or ("A value is present." if present else "This profile value is required to assess the condition."),
            source=rule.source,
            actual_value=profile.get(rule.field),
            expected_value="present",
        )

    if rule.field not in profile or profile[rule.field] is None or profile[rule.field] == "":
        return ConditionResult(
            rule_id=rule.rule_id,
            field=rule.field,
            status=ConditionStatus.MISSING,
            required=rule.required,
            explanation=rule.explanation or "The profile does not contain enough information to assess this condition.",
            source=rule.source,
            expected_value=rule.expected,
        )

    actual = profile[rule.field]
    try:
        if rule.operator == "eq":
            passed = actual == rule.expected
        elif rule.operator == "neq":
            passed = actual != rule.expected
        elif rule.operator == "in":
            passed = actual in rule.expected
        elif rule.operator == "not_in":
            passed = actual not in rule.expected
        elif rule.operator == "gte":
            passed = actual >= rule.expected
        elif rule.operator == "gt":
            passed = actual > rule.expected
        elif rule.operator == "lte":
            passed = actual <= rule.expected
        elif rule.operator == "lt":
            passed = actual < rule.expected
        else:  # Defensive: operator validation above should make this unreachable.
            return ConditionResult(
                rule_id=rule.rule_id, field=rule.field,
                status=ConditionStatus.UNSUPPORTED, required=rule.required,
                explanation="Unsupported rule operator.", source=rule.source,
                actual_value=actual, expected_value=rule.expected,
            )
    except (TypeError, ValueError):
        return ConditionResult(
            rule_id=rule.rule_id,
            field=rule.field,
            status=ConditionStatus.CONFLICT,
            required=rule.required,
            explanation=rule.explanation or "The profile value and rule use incompatible types; verify the data.",
            source=rule.source,
            actual_value=actual,
            expected_value=rule.expected,
        )

    return ConditionResult(
        rule_id=rule.rule_id,
        field=rule.field,
        status=ConditionStatus.PASS if passed else ConditionStatus.FAIL,
        required=rule.required,
        explanation=rule.explanation or ("Condition satisfied." if passed else "Condition not satisfied."),
        source=rule.source,
        actual_value=actual,
        expected_value=rule.expected,
    )


def evaluate_eligibility(scheme: SchemeRuleSet, profile: Mapping[str, Any]) -> EligibilityResult:
    """Evaluate one reviewed rule set against user-provided profile facts.

    Safety policy:
    - Unreviewed scheme rules never yield a definitive ELIGIBLE result.
    - A required FAIL makes the result NOT_ELIGIBLE.
    - Missing/conflicting/unsupported required conditions make it insufficient.
    - Optional conditions remain visible but do not determine the overall status.
    - Empty rules never produce an eligibility claim.
    """
    results = tuple(_evaluate_rule(rule, profile) for rule in scheme.rules)

    if not scheme.reviewed:
        status = EligibilityStatus.INSUFFICIENT_INFORMATION
        summary = "Rules have not been reviewed; no eligibility conclusion can be made."
    elif not results:
        status = EligibilityStatus.INSUFFICIENT_INFORMATION
        summary = "No reviewed conditions are available; no eligibility conclusion can be made."
    else:
        blocking = [r for r in results if r.required]
        if any(r.status == ConditionStatus.FAIL for r in blocking):
            status = EligibilityStatus.NOT_ELIGIBLE
            summary = "At least one required condition was not satisfied."
        elif any(r.status in {ConditionStatus.MISSING, ConditionStatus.CONFLICT, ConditionStatus.UNSUPPORTED} for r in blocking):
            status = EligibilityStatus.INSUFFICIENT_INFORMATION
            summary = "More information or a reviewed rule is needed before eligibility can be assessed."
        elif all(r.status in {ConditionStatus.PASS, ConditionStatus.NOT_APPLICABLE} for r in blocking):
            # Do not claim eligible if any required rule has an unrecognized status.
            status = EligibilityStatus.ELIGIBLE
            summary = "All evaluated required conditions passed. Confirm details with the official scheme authority."
        else:
            status = EligibilityStatus.INSUFFICIENT_INFORMATION
            summary = "The available conditions do not support a definitive conclusion."

    return EligibilityResult(
        scheme_id=scheme.scheme_id,
        scheme_name=scheme.scheme_name,
        rule_version=scheme.version,
        status=status,
        conditions=results,
        summary=summary,
        reviewed=scheme.reviewed,
    )
