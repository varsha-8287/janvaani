
import os
from dataclasses import dataclass

from fastapi import Header, HTTPException, status


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
    if os.getenv("JANVAANI_DEV_AUTH") != "true":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # This is a local-only placeholder, not real token verification.
    if authorization != "Bearer local-dev-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid development token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(uid="local-dev-user")
