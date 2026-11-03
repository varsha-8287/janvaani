
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import CurrentUser, get_current_user
from app.api.profile import ProfileResponse, ProfileUpdate
from app.database.models import Profile
from app.database.session import get_db

router = APIRouter(prefix="/profiles", tags=["Profiles"])


def get_or_create_profile(db: Session, uid: str) -> Profile:
    """Find a user's profile or create a default profile."""
    profile = db.scalars(
        select(Profile).where(Profile.firebase_uid == uid)
    ).first()

    if profile is not None:
        return profile

    profile = Profile(
        firebase_uid=uid,
        preferred_language="en",
        attributes={},
    )
    db.add(profile)

    try:
        db.commit()
        db.refresh(profile)
    except SQLAlchemyError:
        db.rollback()
        # Another request may have created this profile concurrently.
        profile = db.scalars(
            select(Profile).where(Profile.firebase_uid == uid)
        ).first()
        if profile is None:
            raise HTTPException(
                status_code=500,
                detail="Could not create profile",
            )

    return profile


@router.get("/me", response_model=ProfileResponse)
def read_my_profile(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_or_create_profile(db, user.uid)


@router.patch("/me", response_model=ProfileResponse)
def update_my_profile(
    updates: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_or_create_profile(db, user.uid)
    changes = updates.model_dump(exclude_unset=True)

    # Do not allow null for fields that require actual values.
    for field in ("preferred_language", "attributes"):
        if field in changes and changes[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    for field, value in changes.items():
        setattr(profile, field, value)

    if changes:
        try:
            db.commit()
            db.refresh(profile)
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Could not update profile",
            )

    return profile


@router.put("/me", response_model=ProfileResponse)
def replace_my_profile(
    updates: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_my_profile(updates=updates, user=user, db=db)

