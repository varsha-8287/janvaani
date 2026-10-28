
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import get_current_user
from app.database.models import SchemeVersion, SourceDocument
from app.database.session import get_db
from app.main import app


@pytest.fixture
def criteria_client():
    db = MagicMock()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: type(
        "User", (), {"uid": "test-user"}
    )()

    with TestClient(app) as client:
        yield client, db

    app.dependency_overrides.clear()


def make_records(status="draft"):
    version_id = uuid4()
    source_id = uuid4()
    retrieved_at = datetime.now(timezone.utc)

    version = SchemeVersion(
        id=version_id,
        review_status=status,
        eligibility_criteria=None,
    )

    source = SourceDocument(
        id=source_id,
        scheme_version_id=version_id,
        source_url="https://example.gov.in/scheme",
        retrieved_at=retrieved_at,
        review_status="pending",
    )

    return version, source


def make_criteria(source):
    return {
        "eligibility_criteria": {
            "schema_version": 1,
            "logic": "all",
            "rules": [
                {
                    "rule_id": "minimum_age",
                    "profile_field": "age",
                    "operator": "gte",
                    "expected_value": 18,
                    "explanation": "Applicant must be at least 18.",
                    "required": True,
                    "source": {
                        "source_document_id": str(source.id),
                        "source_url": source.source_url,
                        "retrieved_at": source.retrieved_at.isoformat(),
                        "source_title": "Official guidelines",
                    },
                }
            ],
        }
    }


def test_update_criteria_saves_valid_draft(criteria_client):
    client, db = criteria_client
    version, source = make_records()
    db.scalar.side_effect = [version, source]

    response = client.put(
        f"/review/versions/{version.id}/eligibility-criteria",
        json=make_criteria(source),
    )

    assert response.status_code == 200, response.text
    assert version.eligibility_criteria["schema_version"] == 1
    db.commit.assert_called_once()


def test_update_criteria_rejects_non_draft(criteria_client):
    client, db = criteria_client
    version, _ = make_records(status="pending_review")
    db.scalar.return_value = version

    response = client.put(
        f"/review/versions/{version.id}/eligibility-criteria",
        json={"eligibility_criteria": {}},
    )

    assert response.status_code == 409
    db.commit.assert_not_called()


def test_update_criteria_rejects_invalid_contract(criteria_client):
    client, db = criteria_client
    version, _ = make_records()
    db.scalar.return_value = version

    response = client.put(
        f"/review/versions/{version.id}/eligibility-criteria",
        json={"eligibility_criteria": {"schema_version": 1, "rules": []}},
    )

    assert response.status_code == 422
    db.commit.assert_not_called()


def test_update_criteria_rejects_source_from_another_version(criteria_client):
    client, db = criteria_client
    version, source = make_records()
    db.scalar.side_effect = [version, None]

    response = client.put(
        f"/review/versions/{version.id}/eligibility-criteria",
        json=make_criteria(source),
    )

    assert response.status_code == 422
    assert "does not belong" in response.json()["detail"]
    db.commit.assert_not_called()


def test_update_criteria_rejects_source_url_mismatch(criteria_client):
    client, db = criteria_client
    version, source = make_records()
    db.scalar.side_effect = [version, source]

    payload = make_criteria(source)
    payload["eligibility_criteria"]["rules"][0]["source"]["source_url"] = (
        "https://different.gov.in/scheme"
    )

    response = client.put(
        f"/review/versions/{version.id}/eligibility-criteria",
        json=payload,
    )

    assert response.status_code == 422
    assert "URL mismatch" in response.json()["detail"]
    db.commit.assert_not_called()


def test_update_criteria_rolls_back_on_commit_failure(criteria_client):
    client, db = criteria_client
    version, source = make_records()
    db.scalar.side_effect = [version, source]
    db.commit.side_effect = SQLAlchemyError("simulated failure")

    response = client.put(
        f"/review/versions/{version.id}/eligibility-criteria",
        json=make_criteria(source),
    )

    assert response.status_code == 500
    db.rollback.assert_called_once()


def test_update_criteria_rejects_source_timestamp_mismatch(criteria_client):
    client, db = criteria_client
    version, source = make_records()
    db.scalar.side_effect = [version, source]

    payload = make_criteria(source)
    payload["eligibility_criteria"]["rules"][0]["source"]["retrieved_at"] = (
        "2025-01-01T00:00:00+00:00"
    )

    response = client.put(
        f"/review/versions/{version.id}/eligibility-criteria",
        json=payload,
    )

    assert response.status_code == 422
    assert "timestamp mismatch" in response.json()["detail"]
    db.commit.assert_not_called()

