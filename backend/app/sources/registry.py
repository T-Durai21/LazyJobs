import logging
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Job, Profile, SourceRun, utcnow
from . import ats, himalayas, remotive, tracker_csv
from .base import Posting

log = logging.getLogger(__name__)

SOURCES = {
    tracker_csv.NAME: tracker_csv.fetch,
    remotive.NAME: remotive.fetch,
    himalayas.NAME: himalayas.fetch,
    ats.NAME: ats.fetch,
}
# The local CSV costs nothing to re-read, so it is exempt from the refresh floor.
UNTHROTTLED = {tracker_csv.NAME}


def refresh(db: Session, profile: Profile, limit: int = 25000) -> dict[str, str]:
    report = {}
    now = utcnow()
    for name, fetch in SOURCES.items():
        run = db.get(SourceRun, name)
        floor = timedelta(hours=settings.source_min_refresh_hours)
        if run and name not in UNTHROTTLED and now - run.last_run_at < floor:
            report[name] = f"skipped, last fetched {run.last_run_at:%Y-%m-%d %H:%M} UTC"
            continue
        try:
            postings = fetch(profile, limit)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            log.warning("source %s failed: %s", name, exc)
            report[name] = f"failed: {type(exc).__name__}"
            continue
        upsert(db, postings)
        if run is None:
            run = SourceRun(source=name)
            db.add(run)
        run.last_run_at, run.last_count = now, len(postings)
        db.commit()
        report[name] = f"{len(postings)} postings"
    return report


def upsert(db: Session, postings: list[Posting]) -> None:
    ids = {(p.source, p.external_id) for p in postings}
    existing = {
        (job.source, job.external_id): job
        for job in db.scalars(select(Job).where(Job.external_id.in_([i for _, i in ids])))
    }
    for posting in postings:
        job = existing.get((posting.source, posting.external_id))
        if job is None:
            job = Job(source=posting.source, external_id=posting.external_id)
            db.add(job)
            existing[(posting.source, posting.external_id)] = job
        for field in ("url", "apply_url", "title", "company", "locations", "remote", "employment_type",
                      "description", "posted_at", "salary_text", "salary_max_usd"):
            setattr(job, field, getattr(posting, field))
        job.fetched_at = datetime.utcnow()
