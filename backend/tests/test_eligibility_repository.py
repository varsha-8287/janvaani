
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.eligibility.repository import (
    ReviewRequiredError,
    load_reviewed_scheme,
)


def make_repository_records(
    *,
    scheme_status="published",
    version_status="approved",
    source_status="verified",
    version_number=1,
    source_url="https://example.gov.in/scheme",
):
    scheme_id = uuid4()
    version_id = uuid4()
    source_id = uuid4()
    retrieved_at = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)

    criteria = {
        "schema_version": 1,
        "logic": "all",
        "rules": [
            {
                "rule_id": "minimum-age",
                "profile_field": "age",
                "operator": "gte",
                "expected_value": 18,
                "explanation": "Applicant must be at least 18.",
                "source": {
                    "source_document_id": str(source_id),
                    "source_url": source_url,
                    "retrieved_at": retrieved_at.isoformat(),
                    "source_title": "Official scheme guidelines",
                },
            }
        ],
    }

    version = SimpleNamespace(
        id=version_id,
        scheme_id=scheme_id,
        version_number=version_number,
        review_status=version_status,
        eligibility_criteria=criteria,
    )

    scheme = SimpleNamespace(
        id=scheme_id,
        status=scheme_status,
        versions=[version],
        title="Test Scheme",
    )

    source = SimpleNamespace(
        id=source_id,
        scheme_version_id=version_id,
        source_url=source_url,
        retrieved_at=retrieved_at,
        review_status=source_status,
    )

    db = MagicMock()
    db.scalars.return_value.unique.return_value.one_or_none.return_value = scheme
    db.scalar.return_value = source

    return db, scheme, version, source


def test_rejects_unpublished_scheme():
    db, _, _, _ = make_repository_records(scheme_status="draft")

    with pytest.raises(ReviewRequiredError, match="not published"):
        load_reviewed_scheme(db, str(uuid4()))


def test_rejects_scheme_without_approved_version():
    db, scheme, _, _ = make_repository_records(
        version_status="pending_review"
    )

    with pytest.raises(ReviewRequiredError, match="No approved"):
        load_reviewed_scheme(db, str(scheme.id))


def test_rejects_unverified_source_document():
    db, scheme, _, _ = make_repository_records(source_status="pending")

    with pytest.raises(ReviewRequiredError, match="not verified"):
        load_reviewed_scheme(db, str(scheme.id))


def test_rejects_source_url_mismatch():
    db, scheme, _, source = make_repository_records()

    source.source_url = "https://example.gov.in/different-page"

    with pytest.raises(ReviewRequiredError, match="URL mismatch"):
        load_reviewed_scheme(db, str(scheme.id))


def test_loads_approved_version_and_verifies_source():
    db, scheme, version, source = make_repository_records()

    loaded_scheme, loaded_version, logic, rules = load_reviewed_scheme(
        db, str(scheme.id)
    )

    assert loaded_scheme is scheme
    assert loaded_version is version
    assert logic == "all"
    assert len(rules) == 1
    assert rules[0].rule_id == "minimum-age"
    assert rules[0].source.source_url == source.source_url
    assert rules[0].source.rule_version == str(version.version_number)


def test_selects_latest_approved_version_not_newer_draft():
    db, scheme, approved_v1, source = make_repository_records(
        version_number=1,
    )

    approved_v2 = SimpleNamespace(
        id=uuid4(),
        scheme_id=scheme.id,
        version_number=2,
        review_status="approved",
        eligibility_criteria=approved_v1.eligibility_criteria,
    )

    draft_v3 = SimpleNamespace(
        id=uuid4(),
        scheme_id=scheme.id,
        version_number=3,
        review_status="draft",
        eligibility_criteria=approved_v1.eligibility_criteria,
    )

    scheme.versions = [approved_v1, approved_v2, draft_v3]

    loaded_scheme, loaded_version, _, _ = load_reviewed_scheme(
        db, str(scheme.id)
    )

    assert loaded_scheme is scheme
    assert loaded_version is approved_v2
    assert loaded_version.version_number == 2
    assert loaded_version.review_status == "approved"
