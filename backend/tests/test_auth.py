
import pytest
from fastapi import HTTPException

from app.api import auth
from app.api.auth import CurrentUser


@pytest.fixture(autouse=True)
def disable_development_auth(monkeypatch):
    monkeypatch.setattr(auth.settings, "JANVAANI_DEV_AUTH", "false")
    monkeypatch.setattr(
        auth.settings, "JANVAANI_DEV_REVIEWER_AUTH", "false"
    )


def test_missing_citizen_token_returns_401():
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(None)

    assert exc.value.status_code == 401


def test_invalid_firebase_token_returns_401(monkeypatch):
    def reject_token(token):
        raise ValueError("Invalid token")

    monkeypatch.setattr(auth, "_verify_firebase_token", reject_token)

    with pytest.raises(HTTPException) as exc:
        auth.get_current_user("Bearer invalid-token")

    assert exc.value.status_code == 401


def test_valid_firebase_token_returns_verified_uid(monkeypatch):
    monkeypatch.setattr(
        auth,
        "_verify_firebase_token",
        lambda token: {"uid": "firebase-citizen-123"},
    )

    user = auth.get_current_user("Bearer valid-token")

    assert user == CurrentUser(uid="firebase-citizen-123")


def test_token_without_uid_returns_401(monkeypatch):
    monkeypatch.setattr(
        auth,
        "_verify_firebase_token",
        lambda token: {"sub": "some-user"},
    )

    with pytest.raises(HTTPException) as exc:
        auth.get_current_user("Bearer valid-token")

    assert exc.value.status_code == 401


def test_citizen_without_reviewer_claim_gets_403(monkeypatch):
    monkeypatch.setattr(
        auth,
        "_verify_firebase_token",
        lambda token: {"uid": "firebase-citizen-123"},
    )

    with pytest.raises(HTTPException) as exc:
        auth.get_current_reviewer("Bearer valid-token")

    assert exc.value.status_code == 403


def test_reviewer_with_trusted_claim_is_accepted(monkeypatch):
    monkeypatch.setattr(
        auth,
        "_verify_firebase_token",
        lambda token: {
            "uid": "firebase-reviewer-123",
            "reviewer": True,
        },
    )

    user = auth.get_current_reviewer("Bearer valid-token")

    assert user == CurrentUser(uid="firebase-reviewer-123")


def test_development_token_is_rejected_when_disabled():
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user("Bearer local-dev-token")

    assert exc.value.status_code == 401


def test_reviewer_development_token_is_rejected_when_disabled():
    with pytest.raises(HTTPException) as exc:
        auth.get_current_reviewer("Bearer local-reviewer-token")

    assert exc.value.status_code == 401
