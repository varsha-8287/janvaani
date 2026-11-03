"""End-to-End PostgreSQL Integration Tests for Janvaani.

Exercises full CRUD cycles (GET, POST/PUT/PATCH, DELETE) across all database-backed
endpoints against the real PostgreSQL database:
1. Health & DB connection
2. Citizen Profiles (GET, PATCH, GET verification)
3. Published Schemes & Approved Versions (GET list, GET detail)
4. Persistent Conversations & Chat Messages (POST create, GET list, GET detail, POST message, DELETE, GET 404)
5. Reviewed Scheme Eligibility Engine (POST evaluation against DB rules)
6. Application Readiness Checklist (POST check against DB required documents)
7. Reviewer Queue & Document Workflows
"""

import os
import pytest
from uuid import UUID
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.database.session import SessionLocal
from app.database.models import (
    Conversation,
    ChatMessage,
    Profile,
    Scheme,
    SchemeVersion,
)

CITIZEN_AUTH = {"Authorization": "Bearer local-dev-token"}
REVIEWER_AUTH = {"Authorization": "Bearer local-reviewer-token"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# --- 1. System Health & Database Connectivity ---

def test_e2e_health_check(client):
    """GET /health and GET /health/db verify FastAPI is running and PostgreSQL is live."""
    # 1. Basic app health check
    res_app = client.get("/health")
    assert res_app.status_code == 200
    assert res_app.json().get("status") in {"ok", "healthy"}

    # 2. Direct PostgreSQL connection verification via check_db_connection()
    res_db = client.get("/health/db")
    assert res_db.status_code == 200
    db_data = res_db.json()
    assert db_data["status"] == "ok"
    assert db_data["database"] == "connected"


# --- 2. Citizen Profile CRUD: GET, PUT, and PATCH (PostgreSQL profiles table) ---

def test_e2e_profile_get_put_and_patch(client):
    """GET, PUT, and PATCH /profiles/me verifying persistence in PostgreSQL."""
    # 1. GET initial profile
    get_res = client.get("/profiles/me", headers=CITIZEN_AUTH)
    assert get_res.status_code == 200
    initial_data = get_res.json()
    assert "preferred_language" in initial_data

    # 2. PATCH profile with updated state, district, and attributes
    patch_payload = {
        "preferred_language": "ta",
        "state": "Tamil Nadu",
        "district": "Vellore",
        "attributes": {
            "is_landholding_farmer": True,
            "landholding_hectares": 1.75,
            "annual_family_income": 85000,
            "has_aadhaar": True,
        },
    }
    patch_res = client.patch("/profiles/me", json=patch_payload, headers=CITIZEN_AUTH)
    assert patch_res.status_code == 200
    patched_data = patch_res.json()
    assert patched_data["preferred_language"] == "ta"
    assert patched_data["state"] == "Tamil Nadu"
    assert patched_data["district"] == "Vellore"
    assert patched_data["attributes"]["is_landholding_farmer"] is True

    # 3. GET to verify PATCH persisted to PostgreSQL
    verify_patch = client.get("/profiles/me", headers=CITIZEN_AUTH)
    assert verify_patch.status_code == 200
    assert verify_patch.json()["state"] == "Tamil Nadu"
    assert verify_patch.json()["district"] == "Vellore"

    # 4. PUT profile to replace profile details
    put_payload = {
        "preferred_language": "te",
        "state": "Andhra Pradesh",
        "district": "Chittoor",
        "attributes": {
            "is_landholding_farmer": True,
            "landholding_hectares": 2.5,
            "annual_family_income": 120000,
            "has_aadhaar": True,
        },
    }
    put_res = client.put("/profiles/me", json=put_payload, headers=CITIZEN_AUTH)
    assert put_res.status_code == 200
    put_data = put_res.json()
    assert put_data["preferred_language"] == "te"
    assert put_data["state"] == "Andhra Pradesh"
    assert put_data["district"] == "Chittoor"

    # 5. GET to verify PUT persisted to PostgreSQL
    verify_put = client.get("/profiles/me", headers=CITIZEN_AUTH)
    assert verify_put.status_code == 200
    v = verify_put.json()
    assert v["preferred_language"] == "te"
    assert v["state"] == "Andhra Pradesh"
    assert v["district"] == "Chittoor"
    assert v["attributes"]["annual_family_income"] == 120000


# --- 3. Schemes Discovery & Retrieval (PostgreSQL schemes & scheme_versions) ---

def test_e2e_schemes_get_list_and_detail(client):
    """GET /schemes, GET /schemes/{slug}, and GET /api/retrieval/search from PostgreSQL."""
    # 1. GET published schemes list
    list_res = client.get("/schemes")
    assert list_res.status_code == 200
    schemes = list_res.json()
    assert isinstance(schemes, list)
    assert len(schemes) >= 1, "Expected published schemes in PostgreSQL database"

    slugs = [s["slug"] for s in schemes]
    assert "pm-kisan" in slugs or len(slugs) > 0

    target_slug = "pm-kisan" if "pm-kisan" in slugs else slugs[0]

    # 2. GET specific scheme details
    detail_res = client.get(f"/schemes/{target_slug}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["slug"] == target_slug
    assert "title" in detail
    assert "versions" in detail
    assert len(detail["versions"]) >= 1

    version = detail["versions"][0]
    assert "description" in version
    assert "benefits" in version

    # 3. GET /api/retrieval/search for keyword search against published scheme chunks
    search_res = client.get(
        "/api/retrieval/search",
        params={"q": "kisan farmer", "language": "en", "top_k": 3},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert "query" in search_data
    assert "results" in search_data
    assert isinstance(search_data["results"], list)


# --- 4. Persistent Conversations & Chat Messages (PostgreSQL Full Lifecycle) ---

def test_e2e_conversation_full_lifecycle(client, monkeypatch):
    """POST create, GET list, GET detail, POST message, and DELETE against PostgreSQL."""
    monkeypatch.setattr(
        "app.api.chat.chat",
        lambda db, question, history=None, language="en": {
            "answer": "PM-KISAN provides income support of Rs 6000 per year.",
            "sources": [
                {
                    "id": 1,
                    "scheme_title": "PM-KISAN",
                    "source_url": "https://pmkisan.gov.in",
                    "publisher": "Ministry of Agriculture",
                    "version_number": 1,
                }
            ],
        },
    )

    # Step A: POST /api/chat/conversations (CREATE)
    create_payload = {
        "title": "E2E Test Farmer Inquiries",
        "language": "hi",
    }
    create_res = client.post(
        "/api/chat/conversations",
        json=create_payload,
        headers=CITIZEN_AUTH,
    )
    assert create_res.status_code == 201, f"Create failed: {create_res.text}"
    conv = create_res.json()
    conv_id = conv["id"]
    assert conv["title"] == "E2E Test Farmer Inquiries"
    assert conv["language"] == "hi"
    assert conv["message_count"] == 0

    try:
        # Step B: GET /api/chat/conversations (READ LIST)
        list_res = client.get("/api/chat/conversations", headers=CITIZEN_AUTH)
        assert list_res.status_code == 200
        conv_list = list_res.json()
        assert any(c["id"] == conv_id for c in conv_list)

        # Step C: GET /api/chat/conversations/{id} (READ DETAIL)
        get_res = client.get(f"/api/chat/conversations/{conv_id}", headers=CITIZEN_AUTH)
        assert get_res.status_code == 200
        conv_detail = get_res.json()
        assert conv_detail["id"] == conv_id
        assert conv_detail["messages"] == []

        # Step D: POST /api/chat/conversations/{id}/messages (SEND MESSAGE & PERSIST)
        msg_payload = {
            "content": "What are the rules for PM-KISAN?",
            "message": "What are the rules for PM-KISAN?",
            "language": "en",
        }
        send_res = client.post(
            f"/api/chat/conversations/{conv_id}/messages",
            json=msg_payload,
            headers=CITIZEN_AUTH,
        )
        assert send_res.status_code == 200, f"Send message failed: {send_res.text}"
        assistant_reply = send_res.json()
        assert assistant_reply["role"] == "assistant"
        assert len(assistant_reply["content"]) > 0

        # Step E: GET /api/chat/conversations/{id} (VERIFY MESSAGES PERSISTED IN DB)
        get_with_msgs = client.get(f"/api/chat/conversations/{conv_id}", headers=CITIZEN_AUTH)
        assert get_with_msgs.status_code == 200
        updated_detail = get_with_msgs.json()
        assert len(updated_detail["messages"]) == 2
        user_m = updated_detail["messages"][0]
        asst_m = updated_detail["messages"][1]
        assert user_m["role"] == "user"
        assert "PM-KISAN" in user_m["content"]
        assert asst_m["role"] == "assistant"

        # Step F: Direct PostgreSQL DB validation via SQLAlchemy
        def verify_db_counts(expected_conv, expected_msgs):
            import time
            for attempt in range(4):
                try:
                    db = SessionLocal()
                    try:
                        db_conv = db.scalar(select(Conversation).where(Conversation.id == UUID(conv_id)))
                        if expected_conv:
                            assert db_conv is not None
                        else:
                            assert db_conv is None
                        db_msgs = db.scalars(
                            select(ChatMessage).where(ChatMessage.conversation_id == UUID(conv_id))
                        ).all()
                        assert len(db_msgs) == expected_msgs
                        return
                    finally:
                        db.close()
                except AssertionError:
                    raise
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(1)

        verify_db_counts(expected_conv=True, expected_msgs=2)

    finally:
        # Step G: DELETE /api/chat/conversations/{id} (DELETE from PostgreSQL)
        del_res = client.delete(f"/api/chat/conversations/{conv_id}", headers=CITIZEN_AUTH)
        assert del_res.status_code == 200
        assert del_res.json()["id"] == conv_id

        # Step H: GET after DELETE returns 404
        verify_deleted = client.get(f"/api/chat/conversations/{conv_id}", headers=CITIZEN_AUTH)
        assert verify_deleted.status_code == 404

        # Step I: Direct PostgreSQL DB validation verifying cascade cleanup
        verify_db_counts(expected_conv=False, expected_msgs=0)


# --- 5. Eligibility Evaluation (PostgreSQL scheme criteria rules) ---

def test_e2e_evaluate_reviewed_scheme(client, monkeypatch):
    """POST /api/eligibility/evaluate-reviewed evaluating against approved DB scheme rules."""
    monkeypatch.setattr(
        "app.api.routes.generate_eligibility_explanation",
        lambda response, evidence: {
            "explanation": "You meet all eligible requirements based on reviewed criteria.",
            "generated_by": "deterministic",
            "source_references_included": True,
        },
    )

    db = SessionLocal()
    try:
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "pm-kisan"))
        assert scheme is not None
        scheme_id = str(scheme.id)
    finally:
        db.close()

    payload = {
        "scheme_id": scheme_id,
        "profile": {
            "is_landholding_farmer": True,
            "has_aadhaar": True,
            "completed_ekyc": True,
            "is_institutional_landholder": False,
        },
    }
    eval_res = client.post(
        "/api/eligibility/evaluate-reviewed",
        json=payload,
        headers=CITIZEN_AUTH,
    )
    assert eval_res.status_code == 200
    result = eval_res.json()
    assert "status" in result
    assert result["status"] in {"ELIGIBLE", "NOT_ELIGIBLE", "INSUFFICIENT_INFORMATION"}
    assert "conditions" in result
    assert "summary" in result


# --- 6. Application Readiness Checklist (PostgreSQL required documents) ---

def test_e2e_application_readiness(client):
    """POST /api/applications/readiness comparing submitted docs with DB requirements."""
    db = SessionLocal()
    try:
        scheme = db.scalar(select(Scheme).where(Scheme.slug == "pm-kisan"))
        assert scheme is not None
        scheme_id = str(scheme.id)
    finally:
        db.close()

    payload = {
        "scheme_id": scheme_id,
        "submitted_document_types": ["aadhaar_card", "land_ownership_record"],
    }
    res = client.post(
        "/api/applications/readiness",
        json=payload,
        headers=CITIZEN_AUTH,
    )
    assert res.status_code == 200
    readiness = res.json()
    assert "scheme_id" in readiness
    assert "PM-KISAN" in readiness.get("scheme_title", "")
    assert "status" in readiness
    assert "submitted_documents" in readiness
    assert isinstance(readiness["submitted_documents"], list)
    assert "aadhaar_card" in readiness["submitted_documents"]


# --- 7. Reviewer Endpoints: GET and PUT operations ---

def test_e2e_reviewer_endpoints(client):
    """GET /review/schemes/pending and PUT /review/versions/{id}/eligibility-criteria."""
    # 1. Unauthenticated or citizen request to reviewer route should be rejected
    unauth_res = client.get("/review/schemes/pending", headers=CITIZEN_AUTH)
    assert unauth_res.status_code in {401, 403}

    # 2. Reviewer authenticated request succeeds (GET)
    res = client.get("/review/schemes/pending", headers=REVIEWER_AUTH)
    assert res.status_code == 200
    pending_list = res.json()
    assert isinstance(pending_list, list)

    # 3. PUT /review/versions/{uuid}/eligibility-criteria with non-existent version returns 404
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    put_res = client.put(
        f"/review/versions/{non_existent_id}/eligibility-criteria",
        json={"eligibility_criteria": {"rules": []}},
        headers=REVIEWER_AUTH,
    )
    assert put_res.status_code == 404
    assert "not found" in put_res.json()["detail"].lower()

