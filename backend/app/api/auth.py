
from dataclasses import dataclass
from functools import lru_cache

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from fastapi import Header, HTTPException, status

from app.config import settings


@dataclass(frozen=True)
class CurrentUser:
    uid: str


@lru_cache(maxsize=1)
def _get_firebase_app():
    """Initialize Firebase Admin once using trusted server credentials."""
    project_id = settings.FIREBASE_PROJECT_ID.strip()

    if not project_id:
        raise RuntimeError("FIREBASE_PROJECT_ID is not configured.")

    try:
        return firebase_admin.get_app()
    except ValueError:
        # Application Default Credentials are preferred in deployed environments.
        credential = credentials.ApplicationDefault()
        return firebase_admin.initialize_app(
            credential,
            {"projectId": project_id},
        )


def _verify_firebase_token(token: str) -> dict:
    """Verify the signature, issuer, audience, and expiry of a Firebase ID token."""
    app = _get_firebase_app()
    return firebase_auth.verify_id_token(
        token,
        app=app,
        check_revoked=True,
    )


def _unauthorized(detail: str = "Invalid or expired authentication token"):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(detail: str = "Reviewer access required"):
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def _get_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise _unauthorized("Missing bearer token")

    scheme, separator, token = authorization.partition(" ")

    if (
        not separator
        or scheme.lower() != "bearer"
        or not token.strip()
        or " " in token.strip()
    ):
        raise _unauthorized("Invalid authorization header")

    return token.strip()


def get_current_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    """Authenticate a citizen with Firebase or an explicitly enabled dev token."""
    if settings.JANVAANI_DEV_AUTH.lower() == "true":
        if authorization == "Bearer local-dev-token":
            return CurrentUser(uid="local-dev-user")

    token = _get_bearer_token(authorization)

    try:
        claims = _verify_firebase_token(token)
    except Exception as exc:
        # Do not expose internal Firebase errors or credential details.
        raise _unauthorized() from exc

    uid = claims.get("uid")
    if not isinstance(uid, str) or not uid.strip():
        raise _unauthorized()

    return CurrentUser(uid=uid)



def get_current_reviewer(
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    """Authenticate a reviewer and require a trusted reviewer role."""
    if settings.JANVAANI_DEV_REVIEWER_AUTH.lower() == "true":
        if authorization == "Bearer local-reviewer-token":
            return CurrentUser(uid="local-dev-reviewer")

        if not authorization:
            raise _forbidden("Reviewer access required")

    token = _get_bearer_token(authorization)

    try:
        claims = _verify_firebase_token(token)
    except Exception as exc:
        raise _unauthorized() from exc

    uid = claims.get("uid")
    if not isinstance(uid, str) or not uid.strip():
        raise _unauthorized()

    if claims.get("reviewer") is not True:
        raise _forbidden()

    return CurrentUser(uid=uid)

