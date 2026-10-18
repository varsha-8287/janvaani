"""Typed data contracts for deterministic eligibility evaluation.

These models deliberately use only the Python standard library so this module can
be tested independently of FastAPI, a database, or an LLM provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class ConditionStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"
    CONFLICT = "CONFLICT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNSUPPORTED = "UNSUPPORTED"


class EligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    CONDITIONALLY_ELIGIBLE = "CONDITIONALLY_ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


@dataclass(frozen=True)
class SourceReference:
    """Provenance for a reviewed rule. Do not fabricate these fields."""
    source_title: str
    source_url: str
    retrieved_on: str
    rule_version: str
    effective_date: str | None = None

    def __post_init__(self) -> None:
        for name in ("source_title", "source_url", "retrieved_on", "rule_version"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")


@dataclass(frozen=True)
class Rule:
    """A single deterministic condition.

    Supported operators: eq, neq, in, not_in, gte, gt, lte, lt, exists.
    `supported=False` forces UNSUPPORTED and is useful while a source/rule is
    awaiting review. `required=False` means a failed or missing condition does
    not by itself block eligibility, but the result remains visible.
    """
    rule_id: str
    field: str
    operator: str
    expected: Any = None
    explanation: str = ""
    source: SourceReference | None = None
    supported: bool = True
    required: bool = True

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("rule_id must not be empty")
        if not self.field.strip():
            raise ValueError("field must not be empty")



@dataclass(frozen=True)
class SchemeRuleSet:
    scheme_id: str
    scheme_name: str
    version: str
    rules: Sequence[Rule] = field(default_factory=tuple)
    reviewed: bool = False
    logic: str = "all"

    def __post_init__(self) -> None:
        if not self.scheme_id.strip() or not self.scheme_name.strip():
            raise ValueError("scheme_id and scheme_name must not be empty")
        if not self.version.strip():
            raise ValueError("version must not be empty")
        if self.logic not in {"all", "any"}:
            raise ValueError("logic must be 'all' or 'any'")



@dataclass(frozen=True)
class ConditionResult:
    rule_id: str
    field: str
    status: ConditionStatus
    required: bool
    explanation: str
    source: SourceReference | None = None
    actual_value: Any = None
    expected_value: Any = None


@dataclass(frozen=True)
class EligibilityResult:
    scheme_id: str
    scheme_name: str
    rule_version: str
    status: EligibilityStatus
    conditions: Sequence[ConditionResult]
    summary: str
    reviewed: bool

    def to_dict(self) -> dict[str, Any]:
        """JSON-friendly representation for an API response."""
        def source_dict(source: SourceReference | None) -> dict[str, Any] | None:
            if source is None:
                return None
            return {
                "source_title": source.source_title,
                "source_url": source.source_url,
                "retrieved_on": source.retrieved_on,
                "rule_version": source.rule_version,
                "effective_date": source.effective_date,
            }

        return {
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "rule_version": self.rule_version,
            "status": self.status.value,
            "summary": self.summary,
            "reviewed": self.reviewed,
            "conditions": [
                {
                    "rule_id": c.rule_id,
                    "field": c.field,
                    "status": c.status.value,
                    "required": c.required,
                    "explanation": c.explanation,
                    "actual_value": c.actual_value,
                    "expected_value": c.expected_value,
                    "source": source_dict(c.source),
                }
                for c in self.conditions
            ],
        }
