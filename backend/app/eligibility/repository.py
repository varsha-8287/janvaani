
"""Database access and evidence verification for eligibility contract v1."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.models import Scheme, SourceDocument
from app.eligibility.models import SourceReference


class SchemeNotFoundError(LookupError):
    """The requested scheme does not exist."""


class ReviewRequiredError(ValueError):
    """The scheme or its criteria are not safe for evaluation."""


def _parse_uuid(value: str, name: str) -> UUID:
    try:
        return UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ReviewRequiredError(f"{name} is not a valid UUID.") from exc


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ReviewRequiredError("Source retrieval timestamp is missing.")

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewRequiredError(
            "Source retrieval timestamp is invalid."
        ) from exc

    if parsed.tzinfo is None:
        raise ReviewRequiredError(
            "Source retrieval timestamp must include a timezone."
        )

    return parsed.astimezone(timezone.utc)


def load_reviewed_scheme(
    db: Session,
    scheme_id: str,
) -> tuple[Scheme, Any, str, tuple]:
    """Load the latest approved version of a published scheme.

    Every rule must have verified source evidence belonging to that version.
    Returns (scheme, version, logic, rules).
    """
    scheme = None
    try:
        scheme_uuid = UUID(scheme_id)
        scheme = db.scalars(
            select(Scheme)
            .where(Scheme.id == scheme_uuid)
            .options(joinedload(Scheme.versions))
        ).unique().one_or_none()
    except (ValueError, TypeError, AttributeError):
        pass

    if scheme is None:
        scheme = db.scalars(
            select(Scheme)
            .where(Scheme.slug == scheme_id)
            .options(joinedload(Scheme.versions))
        ).unique().one_or_none()

    if scheme is None:
        raise SchemeNotFoundError(f"Scheme '{scheme_id}' not found.")

    if scheme.status != "published":
        raise ReviewRequiredError("Scheme is not published.")

    approved_versions = [
        version
        for version in scheme.versions
        if version.review_status == "approved"
    ]

    if not approved_versions:
        raise ReviewRequiredError("No approved scheme version is available.")

    version = max(approved_versions, key=lambda item: item.version_number)

    from .contract import CriteriaValidationError, parse_criteria

    try:
        criteria = version.eligibility_criteria
        logic, rules = parse_criteria(criteria)
    except CriteriaValidationError as exc:
        raise ReviewRequiredError(
            f"Eligibility criteria require review: {exc}"
        ) from exc

    verified_rules = []

    for rule in rules:
        source = next(
            item["source"]
            for item in criteria["rules"]
            if item["rule_id"] == rule.rule_id
        )

        source_uuid = _parse_uuid(
            source["source_document_id"],
            "source_document_id",
        )

        record = db.scalar(
            select(SourceDocument).where(
                SourceDocument.id == source_uuid,
                SourceDocument.scheme_version_id == version.id,
            )
        )

        if record is None:
            raise ReviewRequiredError(
                f"Source evidence for rule '{rule.rule_id}' is missing "
                "or belongs to another scheme version."
            )

        if record.review_status != "verified":
            raise ReviewRequiredError(
                f"Source evidence for rule '{rule.rule_id}' is not verified."
            )

        if record.source_url != source["source_url"]:
            raise ReviewRequiredError(
                f"Source URL mismatch for rule '{rule.rule_id}'."
            )

        claimed_time = _parse_timestamp(source["retrieved_at"])
        stored_time = record.retrieved_at

        if stored_time.tzinfo is None:
            # Database timestamps should be timezone-aware. Treat a naive
            # stored value as UTC rather than trusting the JSON claim.
            stored_time = stored_time.replace(tzinfo=timezone.utc)

        if claimed_time != stored_time.astimezone(timezone.utc):
            raise ReviewRequiredError(
                f"Source retrieval timestamp mismatch for rule '{rule.rule_id}'."
            )

        if rule.source is None:
            raise ReviewRequiredError(
                f"Source provenance for rule '{rule.rule_id}' is missing."
            )

        verified_source = replace(
            rule.source,
            source_url=record.source_url,
            retrieved_on=record.retrieved_at.isoformat(),
            rule_version=str(version.version_number),
        )
        verified_rules.append(replace(rule, source=verified_source))

    return scheme, version, logic, tuple(verified_rules)
