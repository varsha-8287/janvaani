
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.auth import get_current_reviewer, get_current_user
from app.database.models import Scheme, SchemeVersion, SourceDocument
from app.database.session import SessionLocal, get_db
from app.main import app


def override_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
app.dependency_overrides[get_current_user] = lambda: type(
    "TestUser", (), {"uid": "janvaani-synthetic-e2e"}
)()
app.dependency_overrides[get_current_reviewer] = lambda: type(
    "TestReviewer", (), {"uid": "janvaani-synthetic-reviewer"}
)()

slug = f"synthetic-e2e-{uuid4().hex[:12]}"
scheme_id = None
passed = False

try:
    with TestClient(app) as client:
        # 1. Ingest a synthetic scheme.
        response = client.post(
            "/ingestion/schemes",
            json={
                "slug": slug,
                "title": "Synthetic E2E Test Scheme",
                "administering_authority": "Synthetic Test Authority",
                "government_level": "central",
                "language": "en",
                "description": "Synthetic data for an end-to-end test only.",
                "benefits": ["Synthetic benefit"],
                "required_documents": ["Synthetic identity document"],
                "application_process": ["Synthetic application step"],
                "source_url": f"https://example.gov.in/synthetic/{slug}",
                "publisher": "Synthetic Test Authority",
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        scheme_id = data["scheme_id"]
        version_id = data["version_id"]
        source_id = data["source_document_id"]
        print("PASS: ingestion", scheme_id, version_id, source_id)

        # Read the stored timestamp to use the exact provenance value.
        with SessionLocal() as db:
            source = db.scalar(
                select(SourceDocument).where(
                    SourceDocument.id == source_id
                )
            )
            assert source is not None
            source_url = source.source_url
            retrieved_at = source.retrieved_at.isoformat()

        # 2. Attach criteria referencing the actual stored source.
        response = client.put(
            f"/review/versions/{version_id}/eligibility-criteria",
            json={
                "eligibility_criteria": {
                    "schema_version": 1,
                    "logic": "all",
                    "rules": [
                        {
                            "rule_id": "synthetic_minimum_age",
                            "profile_field": "age",
                            "operator": "gte",
                            "expected_value": 18,
                            "explanation": "Synthetic test: age must be at least 18.",
                            "required": True,
                            "source": {
                                "source_document_id": str(source_id),
                                "source_url": source_url,
                                "retrieved_at": retrieved_at,
                                "source_title": "Synthetic test source",
                            },
                        }
                    ],
                }
            },
        )
        assert response.status_code == 200, response.text
        print("PASS: criteria saved")

        # 3. Submit the draft.
        response = client.post(
            f"/review/versions/{version_id}/submit"
        )
        assert response.status_code == 200, response.text
        print("PASS: submitted for review")

        # 4. Verify the synthetic source through the review endpoint.
        response = client.post(
            f"/review/versions/{version_id}/sources/{source_id}/verify"
        )
        assert response.status_code == 200, response.text
        print("PASS: source verification workflow")

        # 5. Approve the synthetic version.
        response = client.post(
            f"/review/versions/{version_id}/approve"
        )
        assert response.status_code == 200, response.text
        print("PASS: approval workflow")

        # 6. Evaluate using the database-backed reviewed criteria.
        response = client.post(
            "/api/eligibility/evaluate-reviewed",
            json={
                "scheme_id": str(scheme_id),
                "profile": {"age": 18},
            },
        )
        assert response.status_code == 200, response.text
        result = response.json()
        print("PASS: reviewed eligibility evaluation")
        print("Evaluation status:", result.get("status"))
        passed = True

finally:
    # Remove only the uniquely identified synthetic test scheme.
    if scheme_id is not None:
        with SessionLocal() as db:
            scheme = db.scalar(
                select(Scheme).where(Scheme.id == scheme_id)
            )
            if scheme is not None and scheme.slug == slug:
                db.delete(scheme)
                db.commit()
                print("CLEANUP: synthetic scheme removed")

    app.dependency_overrides.clear()

if passed:
    print("SUCCESS: complete synthetic workflow passed")
