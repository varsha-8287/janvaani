
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from app.config import settings


@dataclass(frozen=True)
class CurrentUser:
    uid: str


def get_current_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    """Temporary local-development authentication.

    Replace with Firebase ID-token verification before production.
    Disabled unless explicitly enabled in the environment.
    """
    if settings.JANVAANI_DEV_AUTH.lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Local development only; this is not real token verification.
    if authorization != "Bearer local-dev-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid development token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(uid="local-dev-user")
