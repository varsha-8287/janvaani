
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import CurrentUser, get_current_reviewer
from app.database.models import Scheme, SchemeVersion, SourceDocument
from app.database.session import get_db

from app.eligibility.contract import (
    CriteriaValidationError,
    parse_criteria,
)

router = APIRouter(prefix="/review", tags=["Scheme Review"])


@router.get("/schemes/pending")
def list_pending_schemes(
    reviewer: CurrentUser = Depends(get_current_reviewer),
    db: Session = Depends(get_db),
):
    """List scheme versions awaiting reviewer attention."""
    stmt = (
        select(SchemeVersion)
        .options(
            selectinload(SchemeVersion.scheme),
            selectinload(SchemeVersion.source_documents),
        )
        .where(SchemeVersion.review_status == "pending_review")
        .order_by(SchemeVersion.created_at)
    )

    versions = db.scalars(stmt).all()

    return [
        {
            "version_id": str(version.id),
            "scheme_id": str(version.scheme_id),
            "slug": version.scheme.slug,
            "title": version.scheme.title,
            "version_number": version.version_number,
            "language": version.language,
            "review_status": version.review_status,
            "sources": [
                {
                    "source_id": str(source.id),
                    "source_url": source.source_url,
                    "publisher": source.publisher,
                    "review_status": source.review_status,
                }
                for source in version.source_documents
            ],
        }
        for version in versions
    ]


@router.post("/versions/{version_id}/sources/{source_id}/verify")
def verify_source(
    version_id: UUID,
    source_id: UUID,
    reviewer: CurrentUser = Depends(get_current_reviewer),
    db: Session = Depends(get_db),
):
    """Mark a source as verified for the specified version."""
    version = db.scalar(
        select(SchemeVersion).where(SchemeVersion.id == version_id)
    )

    if version is None:
        raise HTTPException(status_code=404, detail="Scheme version not found")

    source = db.scalar(
        select(SourceDocument).where(
            SourceDocument.id == source_id,
            SourceDocument.scheme_version_id == version_id,
        )
    )

    if source is None:
        raise HTTPException(
            status_code=404,
            detail="Source document not found for this version",
        )

    if version.review_status != "pending_review":
        raise HTTPException(
            status_code=409,
            detail="Only versions pending review can have sources verified",
        )

    source.review_status = "verified"

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save source verification",
        ) from exc

    return {
        "message": "Source verified",
        "source_id": str(source.id),
        "review_status": source.review_status,
    }


@router.post("/versions/{version_id}/approve")
def approve_version(
    version_id: UUID,
    reviewer: CurrentUser = Depends(get_current_reviewer),
    db: Session = Depends(get_db),
):
    """Approve a version only when it has verified source documents."""
    version = db.scalar(
        select(SchemeVersion)
        .options(
            selectinload(SchemeVersion.scheme),
            selectinload(SchemeVersion.source_documents),
        )
        .where(SchemeVersion.id == version_id)
    )

    if version is None:
        raise HTTPException(status_code=404, detail="Scheme version not found")

    if version.review_status != "pending_review":
        raise HTTPException(
            status_code=409,
            detail="Only versions pending review can be approved",
        )

    if not version.source_documents or any(
        source.review_status != "verified"
        or not source.source_url
        or not source.retrieved_at
        for source in version.source_documents
    ):
        raise HTTPException(
            status_code=409,
            detail="All source documents must be verified before approval",
        )

    try:
            parse_criteria(version.eligibility_criteria)
    except CriteriaValidationError as exc:
        raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Eligibility criteria require review: {exc}",
    ) from exc

    
    version.review_status = "approved"
    version.scheme.status = "published"

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save scheme approval",
        ) from exc


    return {
        "message": "Scheme version approved",
        "version_id": str(version.id),
        "review_status": version.review_status,
        "scheme_status": version.scheme.status,
    }


@router.post("/versions/{version_id}/reject")
def reject_version(
    version_id: UUID,
    reviewer: CurrentUser = Depends(get_current_reviewer),
    db: Session = Depends(get_db),
):
    """Reject a version awaiting review."""
    version = db.scalar(
        select(SchemeVersion).where(SchemeVersion.id == version_id)
    )

    if version is None:
        raise HTTPException(status_code=404, detail="Scheme version not found")

    if version.review_status != "pending_review":
        raise HTTPException(
            status_code=409,
            detail="Only versions pending review can be rejected",
        )

    version.review_status = "rejected"

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save scheme rejection",
        ) from exc



    return {
        "message": "Scheme version rejected",
        "version_id": str(version.id),
        "review_status": version.review_status,
    }
