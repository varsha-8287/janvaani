
from fastapi.testclient import TestClient

from app.main import app
from app.api.auth import get_current_user, CurrentUser
from app.api.profiles import get_db


client = TestClient(app)


def override_user():
    return CurrentUser(uid="test-user-123")


def test_profile_requires_authentication():
    response = client.get("/profiles/me")
    assert response.status_code == 401


def test_profile_patch_rejects_protected_fields():
    app.dependency_overrides[get_current_user] = override_user

    try:
        response = client.patch(
            "/profiles/me",
            json={"firebase_uid": "someone-else"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_profile_patch_rejects_invalid_language():
    app.dependency_overrides[get_current_user] = override_user

    try:
        response = client.patch(
            "/profiles/me",
            json={"preferred_language": "x"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
