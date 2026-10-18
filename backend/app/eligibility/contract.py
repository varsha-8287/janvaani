
"""Validation and parsing for Janvaani Eligibility Contract v1."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from .models import Rule, SourceReference

CRITERIA_SCHEMA_VERSION = 1

SUPPORTED_OPERATORS = {
    "eq", "neq", "in", "not_in", "gte", "gt", "lte", "lt", "exists"
}


class CriteriaValidationError(ValueError):
    """Raised when stored eligibility criteria do not match contract v1."""


def _non_empty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CriteriaValidationError(f"{name} must be a non-empty string.")
    return value.strip()


def _validate_source_shape(source: Any) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise CriteriaValidationError("Each rule must contain a source object.")

    source_id = _non_empty_string(
        source.get("source_document_id"), "source.source_document_id"
    )
    source_url = _non_empty_string(source.get("source_url"), "source.source_url")
    retrieved_at = _non_empty_string(
        source.get("retrieved_at"), "source.retrieved_at"
    )

    parsed_url = urlparse(source_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise CriteriaValidationError("source.source_url must be an HTTP(S) URL.")

    try:
        datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CriteriaValidationError(
            "source.retrieved_at must be an ISO-8601 timestamp."
        ) from exc

    return {
        **source,
        "source_document_id": source_id,
        "source_url": source_url,
        "retrieved_at": retrieved_at,
    }


def parse_criteria(criteria: Any) -> tuple[str, tuple[Rule, ...]]:
    """Validate contract v1 JSON and return logic plus rules.

    This validates structure only. It does NOT verify database evidence,
    publication status, or scheme-version approval.
    """
    if not isinstance(criteria, dict):
        raise CriteriaValidationError("Eligibility criteria must be a JSON object.")

    if criteria.get("schema_version") != CRITERIA_SCHEMA_VERSION:
        raise CriteriaValidationError("Unsupported criteria schema_version.")

    logic = criteria.get("logic")
    if logic not in {"all", "any"}:
        raise CriteriaValidationError("logic must be 'all' or 'any'.")

    raw_rules = criteria.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise CriteriaValidationError("rules must be a non-empty list.")

    rules: list[Rule] = []
    seen_ids: set[str] = set()

    for index, item in enumerate(raw_rules):
        if not isinstance(item, dict):
            raise CriteriaValidationError(f"rules[{index}] must be an object.")

        rule_id = _non_empty_string(item.get("rule_id"), f"rules[{index}].rule_id")
        if rule_id in seen_ids:
            raise CriteriaValidationError(f"Duplicate rule_id: {rule_id}.")
        seen_ids.add(rule_id)

        field = _non_empty_string(
            item.get("profile_field"), f"rules[{index}].profile_field"
        )
        operator = _non_empty_string(
            item.get("operator"), f"rules[{index}].operator"
        )

        if operator not in SUPPORTED_OPERATORS:
            raise CriteriaValidationError(
                f"Unsupported operator '{operator}' in rule '{rule_id}'."
            )

        if "expected_value" not in item and operator != "exists":
            raise CriteriaValidationError(
                f"Rule '{rule_id}' must define expected_value."
            )

        explanation = item.get("explanation", "")
        if not isinstance(explanation, str):
            raise CriteriaValidationError(
                f"Rule '{rule_id}' explanation must be a string."
            )

        required = item.get("required", True)
        if not isinstance(required, bool):
            raise CriteriaValidationError(
                f"Rule '{rule_id}' required must be a boolean."
            )

        source = _validate_source_shape(item.get("source"))
        source_title = _non_empty_string(
            source.get("source_title", source.get("reference", "")),
            f"rules[{index}].source.reference",
        )

        rules.append(
            Rule(
                rule_id=rule_id,
                field=field,
                operator=operator,
                expected=item.get("expected_value"),
                explanation=explanation,
                source=SourceReference(
                    source_title=source_title,
                    source_url=source["source_url"],
                    retrieved_on=source["retrieved_at"],
                    rule_version="pending-database-verification",
                ),
                supported=True,
                required=required,
            )
        )

    return logic, tuple(rules)
