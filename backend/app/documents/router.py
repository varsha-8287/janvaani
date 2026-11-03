"""API endpoints for document OCR extraction, validation, and review."""

import base64
import binascii
import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import CurrentUser, get_current_user
from app.database.models import Profile
from app.database.session import get_db
from app.documents.ocr_service import (
    MAX_DOCUMENT_BYTES,
    OCRService,
    OCRServiceError,
    OCRValidationError,
)
from app.documents.schemas import DocumentValidationResult, FieldIssue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


class DocumentExtractResponse(BaseModel):
    """Response returned upon document extraction."""

    document_id: str
    document_type: str
    raw_text: str
    fields: dict[str, Any]
    validation: DocumentValidationResult
    profile_conflicts: list[FieldIssue]
    provider: str
    review_required: Literal[True] = True
    authenticity_verified: Literal[False] = False


class DocumentExtractJSONRequest(BaseModel):
    """Optional JSON payload for base64-encoded document uploads."""

    file_base64: str = Field(min_length=1, description="Base64-encoded file content.")
    mime_type: str = Field(default="image/jpeg", description="MIME type of document.")
    document_type: str = Field(default="income_certificate")
    language: str = Field(default="hi")
    preferred_provider: str | None = Field(default=None)


def get_optional_current_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser | None:
    """Optionally authenticate a user if Authorization header is present."""
    if not authorization:
        return None
    try:
        return get_current_user(authorization)
    except HTTPException:
        return None


def get_ocr_service() -> OCRService:
    return OCRService()


@router.post(
    "/extract",
    response_model=DocumentExtractResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_document(
    request: Request,
    document_type: str = Query(default="income_certificate"),
    language: str = Query(default="hi"),
    preferred_provider: str | None = Query(default=None),
    user: CurrentUser | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
    ocr_service: OCRService = Depends(get_ocr_service),
) -> DocumentExtractResponse:
    """Extract text and candidate fields from an uploaded document.

    Accepts raw binary payloads (JPEG, PNG, WebP, PDF) or JSON with file_base64.
    Runs deterministic format validation and flags any conflicts with user profile.
    Citizens must review and confirm extracted data before submission.
    """
    raw_body = await request.body()
    if not raw_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document payload must not be empty.",
        )

    if len(raw_body) > MAX_DOCUMENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Document exceeds maximum allowed size of {MAX_DOCUMENT_BYTES // (1024 * 1024)} MB.",
        )

    content_type_header = request.headers.get("content-type", "").split(";")[0].strip().lower()

    content: bytes
    mime_type: str
    doc_type = document_type
    lang = language
    provider_pref = preferred_provider

    if content_type_header == "application/json":
        try:
            json_data = json.loads(raw_body.decode("utf-8"))
            parsed_req = DocumentExtractJSONRequest(**json_data)
        except (json.JSONDecodeError, ValueError, Exception) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON document payload: {exc}",
            ) from exc

        try:
            content = base64.b64decode(parsed_req.file_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 encoding in file_base64.",
            ) from exc

        mime_type = parsed_req.mime_type.lower().strip()
        doc_type = parsed_req.document_type
        lang = parsed_req.language
        provider_pref = parsed_req.preferred_provider or preferred_provider

    else:
        content = raw_body
        mime_type = content_type_header or "image/jpeg"

    # Profile conflict context for authenticated citizens
    profile_data: dict[str, Any] | None = None
    if user is not None:
        profile = db.scalars(
            select(Profile).where(Profile.firebase_uid == user.uid)
        ).first()
        if profile is not None:
            profile_data = {}
            if profile.attributes:
                profile_data.update(profile.attributes)
            if profile.state:
                profile_data["state"] = profile.state
            if profile.district:
                profile_data["district"] = profile.district

    try:
        result = ocr_service.process_document(
            content=content,
            mime_type=mime_type,
            document_type=doc_type,
            language=lang,
            preferred_provider=provider_pref,
            profile_data=profile_data,
        )
    except OCRValidationError as exc:
        err_msg = str(exc)
        if "Unsupported media type" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=err_msg,
            ) from exc
        if "Unsupported language" in err_msg or "Unsupported document type" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=err_msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        ) from exc
    except OCRServiceError as exc:
        logger.exception("OCR extraction service failure")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Document OCR service failed. Please check document quality and try again.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error processing document OCR")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected server error occurred during document extraction.",
        ) from exc

    return DocumentExtractResponse(**result)
