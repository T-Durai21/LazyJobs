from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import llm
from ..db import get_db
from ..matching import score
from ..models import Application, ApplicationStatus as S, Job, User, utcnow
from ..schemas import ApplicationCreate, ApplicationOut, ApplicationPatch
from ..session import current_user
from .profile import profile_of

router = APIRouter(prefix="/api/applications", tags=["applications"])

# PLAN.md section 5. Nothing reaches submitted except through the user's own PATCH.
TRANSITIONS = {
    S.MATCHED: {S.DRAFTED, S.DISCARDED},
    S.DRAFTED: {S.DRAFTED, S.SUBMITTED, S.DISCARDED},
    S.SUBMITTED: {S.INTERVIEW, S.REJECTED},
    S.INTERVIEW: {S.REJECTED},
    S.REJECTED: set(),
    S.DISCARDED: set(),
}


def check_transition(current: str, target: str) -> None:
    try:
        allowed = TRANSITIONS[S(current)]
        wanted = S(target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown status: {target}") from exc
    if wanted not in allowed:
        raise HTTPException(status_code=409, detail=f"Cannot move from {current} to {target}")


def owned(db: Session, user: User, application_id: int) -> Application:
    application = db.get(Application, application_id)
    if application is None or application.user_id != user.id:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def draft(db: Session, user: User, application: Application) -> None:
    profile = profile_of(db, user)
    match = score(application.job, profile, datetime.utcnow())
    application.cover_letter = llm.draft_cover_letter(profile, application.job, match.matched_skills)
    application.status = S.DRAFTED


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    status: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> list[Application]:
    query = select(Application).where(Application.user_id == user.id).order_by(Application.updated_at.desc())
    if status:
        query = query.where(Application.status == status)
    return list(db.scalars(query))


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(
    body: ApplicationCreate, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Application:
    job = db.get(Job, body.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    duplicate = db.scalars(
        select(Application).where(Application.user_id == user.id, Application.job_id == job.id)
    ).first()
    if duplicate is not None:
        raise HTTPException(status_code=409, detail=f"Already tracked as application {duplicate.id}")
    match = score(job, profile_of(db, user), datetime.utcnow())
    application = Application(user_id=user.id, job=job, score=match.score, match_reason=match.reason)
    db.add(application)
    if body.draft_letter:
        draft(db, user, application)
    db.commit()
    return application


@router.post("/{application_id}/draft", response_model=ApplicationOut)
def draft_letter(
    application_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Application:
    application = owned(db, user, application_id)
    check_transition(application.status, S.DRAFTED)
    draft(db, user, application)
    db.commit()
    return application


@router.patch("/{application_id}", response_model=ApplicationOut)
def patch_application(
    application_id: int,
    changes: ApplicationPatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Application:
    application = owned(db, user, application_id)
    if changes.status is not None and changes.status != application.status:
        check_transition(application.status, changes.status)
        application.status = changes.status
        if changes.status == S.SUBMITTED and application.submitted_at is None:
            application.submitted_at = utcnow()
    if changes.notes is not None:
        application.notes = changes.notes
    if changes.cover_letter is not None:
        application.cover_letter = changes.cover_letter
    db.commit()
    return application
