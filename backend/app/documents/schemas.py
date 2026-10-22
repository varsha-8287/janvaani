
"""Contracts for document evidence and OCR-extracted fields."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceReference(BaseModel):
    """Reference to a specific uploaded document and extracted field."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=128)
    document_type: str = Field(min_length=1, max_length=100)
    field_name: str = Field(min_length=1, max_length=100)
    page: int | None = Field(default=None, ge=1)


class ExtractedDocument(BaseModel):
    """OCR output supplied for validation; not proof of authenticity."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=128)
    document_type: str = Field(min_length=1, max_length=100)
    fields: dict[str, Any] = Field(default_factory=dict)
    extraction_source: Literal["ocr", "manual"] = "ocr"
    page_count: int | None = Field(default=None, ge=1)


class FieldIssue(BaseModel):
    field_name: str
    status: Literal["MISSING", "INVALID", "CONFLICT"]
    explanation: str
    evidence: list[EvidenceReference] = Field(default_factory=list)


class DocumentValidationResult(BaseModel):
    document_id: str
    document_type: str
    valid: bool
    issues: list[FieldIssue] = Field(default_factory=list)
    authenticity_verified: Literal[False] = False
