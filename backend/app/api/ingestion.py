
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

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

        return {
            "message": "Scheme ingested successfully and saved as a draft.",
            "scheme_id": scheme.id,
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
