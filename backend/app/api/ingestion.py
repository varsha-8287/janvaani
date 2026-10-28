
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.models import SchemeVersion, SourceDocument
from app.api.auth import CurrentUser, get_current_user
from app.database.session import get_db
from app.ingestion.schemas import SchemeIngestionInput
from app.ingestion.service import DuplicateSchemeError, ingest_scheme

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.post("/schemes", status_code=status.HTTP_201_CREATED)
def create_scheme_from_ingestion(
    data: SchemeIngestionInput,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ingest a scheme as a draft for review."""
    try:
        scheme = ingest_scheme(db, data)
        db.commit()
        db.refresh(scheme)
        version = db.scalar(
            select(SchemeVersion)
            .where(SchemeVersion.scheme_id == scheme.id)
            .order_by(SchemeVersion.version_number.desc())
        )

        if version is None:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve the created scheme version.",
            )

        source = db.scalar(
            select(SourceDocument)
            .where(SourceDocument.scheme_version_id == version.id)
            .order_by(SourceDocument.retrieved_at.desc())
        )

        if source is None:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve the created source document.",
            )
        return {
            "message": "Scheme ingested successfully and saved as a draft.",
            "scheme_id": str(scheme.id),
            "version_id": str(version.id),
            "source_document_id": str(source.id),
            "slug": scheme.slug,
            "title": scheme.title,
            "status": scheme.status,
        }

    except DuplicateSchemeError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The scheme conflicts with an existing database record.",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the ingested scheme.",
        ) from exc
