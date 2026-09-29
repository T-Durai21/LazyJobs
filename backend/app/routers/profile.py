from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from .. import llm
from ..cv import extract_text
from ..db import get_db
from ..models import Profile, User
from ..schemas import ProfileOut, ProfilePatch
from ..session import current_user
from ..storage import save_cv

router = APIRouter(prefix="/api/profile", tags=["profile"])


def profile_of(db: Session, user: User) -> Profile:
    profile = user.profile
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Profile:
    profile = profile_of(db, user)
    db.commit()
    return profile


@router.patch("", response_model=ProfileOut)
def patch_profile(
    changes: ProfilePatch, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Profile:
    profile = profile_of(db, user)
    for field, value in changes.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    return profile


@router.post("/cv", response_model=ProfileOut)
async def upload_cv(
    file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Profile:
    data = await file.read()
    text = extract_text(file.filename or "", data)
    save_cv(user.id, file.filename or "cv", data)
    profile = profile_of(db, user)
    profile.cv_filename = file.filename or ""
    profile.cv_text = text
    for field, value in llm.extract_profile(text).items():
        setattr(profile, field, value)
    db.commit()
    return profile
