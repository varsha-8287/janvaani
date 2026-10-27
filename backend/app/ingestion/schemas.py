
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SchemeIngestionInput(BaseModel):
    """Validated, structured scheme content awaiting ingestion."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=1, max_length=180)
    title: str = Field(min_length=1, max_length=300)
    administering_authority: str | None = Field(
        default=None, max_length=300
    )
    government_level: str = "central"
    language: str = Field(default="en", min_length=2, max_length=12)
    description: str | None = None
    benefits: list[Any] | dict[str, Any] | None = None
    eligibility_criteria: dict[str, Any] | list[Any] | None = None
    required_documents: list[Any] | dict[str, Any] | None = None
    application_process: list[Any] | dict[str, Any] | None = None
    valid_from: date | None = None
    valid_until: date | None = None

    source_url: str = Field(min_length=1)
    publisher: str | None = Field(default=None, max_length=300)
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    content_hash: str | None = Field(default=None, max_length=128)

    @field_validator("slug", "title", "language", "source_url")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("government_level")
    @classmethod
    def validate_government_level(cls, value: str) -> str:
        if value not in {"central", "state", "local", "other"}:
            raise ValueError("Invalid government level")
        return value

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("source_url must be a valid HTTPS URL")
        return value

    @field_validator("retrieved_at")
    @classmethod
    def normalize_retrieved_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_date_range(self):
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_until < self.valid_from
        ):
            raise ValueError("valid_until must be on or after valid_from")
        return self
