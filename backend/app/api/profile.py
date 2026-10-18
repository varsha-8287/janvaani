
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdate(BaseModel):
    """Fields a user is allowed to update on their profile."""

    model_config = ConfigDict(extra="forbid")

    preferred_language: str | None = Field(
        default=None, min_length=2, max_length=10
    )
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    attributes: dict[str, Any] | None = None


class ProfileResponse(BaseModel):
    """Public profile fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    preferred_language: str
    state: str | None
    district: str | None
    attributes: dict[str, Any]
    created_at: datetime
    updated_at: datetime
