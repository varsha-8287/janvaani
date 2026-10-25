
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.auth import get_current_reviewer
from app.database.models import Scheme, SchemeVersion, SourceDocument
from app.database.session import get_db
from app.main import app


@pytest.fixture
def review_client():
    db = MagicMock()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_reviewer] = lambda: type(
        "Reviewer", (), {"uid": "test-reviewer"}
    )()

    with TestClient(app) as client:
        yield client, db

    app.dependency_overrides.clear()


def valid_review_criteria(source):
    return {
        "schema_version": 1,
        "logic": "all",
        "rules": [
            {
                "rule_id": "age_rule",
                "profile_field": "age",
                "operator": "gte",
                "expected_value": 18,
                "explanation": "Applicant must be at least 18.",
                "required": True,
                "source": {
                    "source_document_id": str(source.id),
                    "source_url": source.source_url,
                    "retrieved_at": source.retrieved_at.isoformat(),
                    "source_title": "Official scheme guidelines",
                },
            }
        ],
    }


def make_review_records(
    *,
    version_status="pending_review",
    source_status="pending",
    criteria=None,
):
    scheme = Scheme(
        id=uuid4(),
        slug="review-test-scheme",
        title="Review Test Scheme",
        government_level="central",
        status="draft",
    )

    version = SchemeVersion(
        id=uuid4(),
        scheme_id=scheme.id,
        version_number=1,
        language="en",
        review_status=version_status,
        eligibility_criteria=(
            criteria if criteria is not None
            else {"schema_version": "1.0"}
        ),
    )
    version.scheme = scheme

    source = SourceDocument(
        id=uuid4(),
        scheme_version_id=version.id,
        source_url="https://example.gov.in/scheme",
        publisher="Test Authority",
        retrieved_at=datetime.now(timezone.utc),
        review_status=source_status,
    )
    source.scheme_version = version
    version.source_documents = [source]

    return scheme, version, source


def test_pending_schemes_returns_empty_list(review_client):
    client, db = review_client
    db.scalars.return_value.all.return_value = []

    response = client.get("/review/schemes/pending")

    assert response.status_code == 200
    assert response.json() == []


def test_review_endpoint_requires_reviewer_authentication():
    client = TestClient(app)

    response = client.get("/review/schemes/pending")

    assert response.status_code == 403


def test_verify_source_returns_404_for_missing_version(review_client):
    client, db = review_client
    db.scalar.return_value = None

    response = client.post(
        f"/review/versions/{uuid4()}/sources/{uuid4()}/verify"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Scheme version not found"


def test_approve_returns_404_for_missing_version(review_client):
    client, db = review_client
    db.scalar.return_value = None

    response = client.post(f"/review/versions/{uuid4()}/approve")

    assert response.status_code == 404


def test_reject_returns_404_for_missing_version(review_client):
    client, db = review_client
    db.scalar.return_value = None

    response = client.post(f"/review/versions/{uuid4()}/reject")

    assert response.status_code == 404


def test_approve_rejects_pending_source(review_client):
    client, db = review_client
    _, version, _ = make_review_records()

    db.scalar.return_value = version

    response = client.post(f"/review/versions/{version.id}/approve")

    assert response.status_code == 409
    assert "verified" in response.json()["detail"]
    db.commit.assert_not_called()


def test_verify_source_rejects_source_from_another_version(review_client):
    client, db = review_client
    _, version, _ = make_review_records()
    db.scalar.side_effect = [version, None]

    response = client.post(
        f"/review/versions/{version.id}/sources/{uuid4()}/verify"
    )

    assert response.status_code == 404
    assert "Source document not found" in response.json()["detail"]
    db.commit.assert_not_called()


def test_approve_rejects_missing_eligibility_schema_version(review_client):
    client, db = review_client
    _, version, _ = make_review_records(
        source_status="verified",
        criteria={"rules": []},
    )

    db.scalar.return_value = version

    response = client.post(f"/review/versions/{version.id}/approve")

    assert response.status_code == 409
    assert "schema_version" in response.json()["detail"]
    db.rollback.assert_not_called()
    db.commit.assert_not_called()


def test_rejected_version_cannot_be_approved(review_client):
    client, db = review_client
    _, version, _ = make_review_records(
        version_status="rejected",
        source_status="verified",
    )

    db.scalar.return_value = version

    response = client.post(f"/review/versions/{version.id}/approve")

    assert response.status_code == 409
    assert "pending review" in response.json()["detail"]
    db.commit.assert_not_called()

    

def test_approve_version_with_verified_source(review_client):
    client, db = review_client
    scheme, version, source = make_review_records(source_status="verified")
    version.eligibility_criteria = valid_review_criteria(source)

    db.scalar.return_value = version

    response = client.post(f"/review/versions/{version.id}/approve")

    assert response.status_code == 200
    assert response.json()["review_status"] == "approved"
    assert response.json()["scheme_status"] == "published"
    assert version.review_status == "approved"
    assert scheme.status == "published"
    db.commit.assert_called_once()


    

def test_approve_rolls_back_on_database_error(review_client):
    from sqlalchemy.exc import SQLAlchemyError

    client, db = review_client
    _, version, source = make_review_records(source_status="verified")
    version.eligibility_criteria = valid_review_criteria(source)

    db.scalar.return_value = version
    db.commit.side_effect = SQLAlchemyError("simulated commit failure")

    response = client.post(f"/review/versions/{version.id}/approve")

    assert response.status_code == 500
    assert response.json()["detail"] == "Could not save scheme approval"
    db.rollback.assert_called_once()




def test_verify_source_rolls_back_on_database_error(review_client):
    from sqlalchemy.exc import SQLAlchemyError

    client, db = review_client
    _, version, source = make_review_records(source_status="pending")

    version.review_status = "pending_review"
    db.scalar.side_effect = [version, source]
    db.commit.side_effect = SQLAlchemyError("simulated commit failure")

    response = client.post(
        f"/review/versions/{version.id}/sources/{source.id}/verify"
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Could not save source verification"
    db.rollback.assert_called_once()



def test_reject_rolls_back_on_database_error(review_client):
    from sqlalchemy.exc import SQLAlchemyError

    client, db = review_client
    _, version, _ = make_review_records()

    db.scalar.return_value = version
    db.commit.side_effect = SQLAlchemyError("simulated commit failure")

    response = client.post(f"/review/versions/{version.id}/reject")

    assert response.status_code == 500
    assert response.json()["detail"] == "Could not save scheme rejection"
    db.rollback.assert_called_once()


def test_approve_rejects_malformed_eligibility_criteria(review_client):
    client, db = review_client
    _, version, _ = make_review_records(
        source_status="verified",
        criteria={
            "schema_version": 1,
            "logic": "all",
            "rules": [],
        },
    )

    db.scalar.return_value = version

    response = client.post(f"/review/versions/{version.id}/approve")

    assert response.status_code == 409
    assert "rules must be a non-empty list" in response.json()["detail"]
    db.commit.assert_not_called()


def test_submit_draft_for_review(review_client):
    client, db = review_client
    _, version, _ = make_review_records(version_status="draft")
    db.scalar.return_value = version

    response = client.post(f"/review/versions/{version.id}/submit")

    assert response.status_code == 200
    assert response.json()["review_status"] == "pending_review"
    assert version.review_status == "pending_review"
    db.commit.assert_called_once()


def test_submit_review_returns_404_for_missing_version(review_client):
    client, db = review_client
    db.scalar.return_value = None

    response = client.post(f"/review/versions/{uuid4()}/submit")

    assert response.status_code == 404
    db.commit.assert_not_called()


def test_submit_review_rejects_non_draft_version(review_client):
    client, db = review_client
    _, version, _ = make_review_records(version_status="pending_review")
    db.scalar.return_value = version

    response = client.post(f"/review/versions/{version.id}/submit")

    assert response.status_code == 409
    assert version.review_status == "pending_review"
    db.commit.assert_not_called()


def test_submit_review_rolls_back_on_commit_failure(review_client):
    from sqlalchemy.exc import SQLAlchemyError

    client, db = review_client
    _, version, _ = make_review_records(version_status="draft")
    db.scalar.return_value = version
    db.commit.side_effect = SQLAlchemyError("database failure")

    response = client.post(f"/review/versions/{version.id}/submit")

    assert response.status_code == 500
    assert version.review_status == "pending_review"
    db.rollback.assert_called_once()
