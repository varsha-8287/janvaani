
"""API endpoint for checking application document readiness."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.applications.readiness import assess_application_readiness
from app.database.models import Scheme
from app.database.session import get_db
from app.documents.schemas import ExtractedDocument


router = APIRouter(
    prefix="/api/applications",
    tags=["Application Readiness"],
)


class ReadinessRequest(BaseModel):
    """Document types declared by the client for a readiness preview."""

    scheme_id: str = Field(min_length=1)
    submitted_document_types: list[str] = Field(
        default_factory=list,
        max_length=50,
    )


@router.post("/readiness")
def check_readiness(
    request: ReadinessRequest,
    db: Session = Depends(get_db),
):
    """Compare declared document types with approved scheme requirements.

    This endpoint does not upload or verify documents. It provides a
    checklist preview based on the document types supplied by the client.
    """
    try:
        scheme_uuid = UUID(request.scheme_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(
            status_code=422,
            detail="scheme_id must be a valid UUID.",
        ) from exc

    scheme = db.scalars(
        select(Scheme)
        .where(Scheme.id == scheme_uuid)
        .options(selectinload(Scheme.versions))
    ).one_or_none()

    if scheme is None or scheme.status != "published":
        raise HTTPException(status_code=404, detail="Published scheme not found.")

    approved_versions = [
        version
        for version in scheme.versions
        if version.review_status == "approved"
    ]

    if not approved_versions:
        raise HTTPException(
            status_code=409,
            detail="No approved scheme version is available.",
        )

    version = max(
        approved_versions,
        key=lambda item: item.version_number,
    )

    submitted = []
    for index, document_type in enumerate(request.submitted_document_types):
        if not isinstance(document_type, str) or not document_type.strip():
            raise HTTPException(
                status_code=422,
                detail="Each submitted document type must be non-empty.",
            )

        submitted.append(
            ExtractedDocument(
                document_id=f"client-declared-{index + 1}",
                document_type=document_type.strip(),
                fields={},
                extraction_source="manual",
            )
        )

    result = assess_application_readiness(
        version.required_documents,
        submitted,
    )

    response = result.model_dump(mode="json")
    response["scheme_id"] = str(scheme.id)
    response["scheme_title"] = scheme.title
    response["scheme_version"] = version.version_number
    response["review_status"] = version.review_status
    response["check_type"] = "document_type_checklist_preview"

    return response
