from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..matching import Match, rank
from ..models import Application, Job, Profile, User
from ..schemas import JobOut, MatchOut
from ..session import current_user
from ..sources.registry import refresh
from .profile import profile_of

router = APIRouter(prefix="/api", tags=["jobs"])

# Ranking every stored posting takes seconds, and the answer only changes when the profile
# is edited or a refresh lands, so the last result is kept per user until either happens.
_ranked_cache: dict[int, tuple[tuple, list[Match]]] = {}


def ranked_for(db: Session, profile: Profile) -> list[Match]:
    job_count, last_fetch = db.execute(select(func.count(Job.id), func.max(Job.fetched_at))).one()
    key = (profile.updated_at, job_count, last_fetch)
    cached = _ranked_cache.get(profile.user_id)
    if cached and cached[0] == key:
        return cached[1]
    ranked = rank(list(db.scalars(select(Job))), profile, datetime.utcnow())
    _ranked_cache[profile.user_id] = (key, ranked)
    return ranked


@router.post("/jobs/refresh")
def refresh_jobs(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    return refresh(db, profile_of(db, user))


@router.get("/matches", response_model=list[MatchOut])
def matches(
    limit: int = 100, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> list[MatchOut]:
    profile = profile_of(db, user)
    applications = {a.job_id: a for a in db.scalars(select(Application).where(Application.user_id == user.id))}
    # Discarded jobs stay hidden; everything else shows its tracker status beside the score.
    ranked = [
        m for m in ranked_for(db, profile)
        if getattr(applications.get(m.job.id), "status", "") != "discarded"
    ][:limit]
    return [
        MatchOut(
            job=JobOut.model_validate(m.job),
            score=m.score,
            reason=m.reason,
            application_id=getattr(applications.get(m.job.id), "id", None),
            application_status=getattr(applications.get(m.job.id), "status", None),
        )
        for m in ranked
    ]
