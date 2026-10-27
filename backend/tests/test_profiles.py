
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


from unittest.mock import MagicMock

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.profiles import get_or_create_profile, update_my_profile
from app.api.profile import ProfileUpdate
from app.database.models import Profile


def test_get_or_create_profile_creates_default_profile():
    db = MagicMock()
    db.scalars.return_value.first.return_value = None

    profile = get_or_create_profile(db, "new-user-123")

    assert profile.firebase_uid == "new-user-123"
    assert profile.preferred_language == "en"
    assert profile.attributes == {}
    db.add.assert_called_once_with(profile)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(profile)


def test_get_or_create_profile_returns_existing_profile():
    db = MagicMock()
    existing_profile = Profile(
        firebase_uid="existing-user",
        preferred_language="ta",
        attributes={"notifications": True},
    )
    db.scalars.return_value.first.return_value = existing_profile

    result = get_or_create_profile(db, "existing-user")

    assert result is existing_profile
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_get_or_create_profile_handles_database_failure():
    db = MagicMock()
    db.scalars.return_value.first.side_effect = [None, None]
    db.commit.side_effect = SQLAlchemyError("database failure")

    try:
        get_or_create_profile(db, "new-user")
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 500
        assert exc.detail == "Could not create profile"

    db.rollback.assert_called_once()


def test_profile_update_changes_preferences():
    db = MagicMock()
    profile = Profile(
        firebase_uid="test-user-123",
        preferred_language="en",
        state=None,
        district=None,
        attributes={},
    )
    db.scalars.return_value.first.return_value = profile

    result = update_my_profile(
        updates=ProfileUpdate(
            preferred_language="ta",
            state="Tamil Nadu",
            district="Chennai",
            attributes={"notifications": True},
        ),
        user=CurrentUser(uid="test-user-123"),
        db=db,
    )

    assert result.preferred_language == "ta"
    assert result.state == "Tamil Nadu"
    assert result.district == "Chennai"
    assert result.attributes == {"notifications": True}
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(profile)


def test_profile_update_rejects_null_required_preferences():
    db = MagicMock()
    profile = Profile(
        firebase_uid="test-user-123",
        preferred_language="en",
        attributes={},
    )
    db.scalars.return_value.first.return_value = profile

    try:
        update_my_profile(
            updates=ProfileUpdate.model_validate({"preferred_language": None}),
            user=CurrentUser(uid="test-user-123"),
            db=db,
        )
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail == "preferred_language cannot be null"


def test_profile_update_handles_database_failure():
    db = MagicMock()
    profile = Profile(
        firebase_uid="test-user-123",
        preferred_language="en",
        attributes={},
    )
    db.scalars.return_value.first.return_value = profile
    db.commit.side_effect = SQLAlchemyError("database failure")

    try:
        update_my_profile(
            updates=ProfileUpdate(preferred_language="ta"),
            user=CurrentUser(uid="test-user-123"),
            db=db,
        )
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 500
        assert exc.detail == "Could not update profile"

    db.rollback.assert_called_once()

