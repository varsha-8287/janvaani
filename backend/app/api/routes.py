
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.database.models import Scheme

router = APIRouter(prefix="/schemes", tags=["Schemes"])


@router.get("")
def list_schemes(
    government_level: str | None = Query(
        default=None,
        description="Filter by central, state, local, or other",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List published schemes that have an approved version."""
    stmt = (
        select(Scheme)
        .options(selectinload(Scheme.versions))
        .where(Scheme.status == "published")
        .where(
            Scheme.versions.any(review_status="approved")
        )
    )

    if government_level:
        allowed_levels = {"central", "state", "local", "other"}
        if government_level not in allowed_levels:
            raise HTTPException(
                status_code=422,
                detail="Invalid government_level",
            )
        stmt = stmt.where(Scheme.government_level == government_level)

    stmt = stmt.order_by(Scheme.title).offset(offset).limit(limit)
    schemes = db.scalars(stmt).all()

    return [
        {
            "slug": scheme.slug,
            "title": scheme.title,
            "administering_authority": scheme.administering_authority,
            "government_level": scheme.government_level,
            "versions": [
                {
                    "version_number": version.version_number,
                    "language": version.language,
                    "description": version.description,
                }
                for version in scheme.versions
                if version.review_status == "approved"
            ],
        }
        for scheme in schemes
    ]


@router.get("/{slug}")
def get_scheme(
    slug: str,
    db: Session = Depends(get_db),
):
    """Get a published scheme and its approved versions."""
    stmt = (
        select(Scheme)
        .options(selectinload(Scheme.versions))
        .where(Scheme.slug == slug)
        .where(Scheme.status == "published")
        .where(Scheme.versions.any(review_status="approved"))
    )
    scheme = db.scalars(stmt).first()

    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")

    approved_versions = [
        {
            "version_number": version.version_number,
            "language": version.language,
            "description": version.description,
            "benefits": version.benefits,
            "eligibility_criteria": version.eligibility_criteria,
            "required_documents": version.required_documents,
            "application_process": version.application_process,
            "valid_from": version.valid_from,
            "valid_until": version.valid_until,
        }
        for version in scheme.versions
        if version.review_status == "approved"
    ]

    return {
        "slug": scheme.slug,
        "title": scheme.title,
        "administering_authority": scheme.administering_authority,
        "government_level": scheme.government_level,
        "versions": approved_versions,
    }
