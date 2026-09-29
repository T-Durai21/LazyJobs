import csv
from datetime import datetime
from pathlib import Path

from ..config import settings
from ..models import Profile
from .base import Posting

NAME = "tracker_csv"


def fetch(profile: Profile, limit: int) -> list[Posting]:
    # A hand-kept spreadsheet of Indeed/Naukri/LinkedIn finds, since those sites have no
    # public API. Columns: No, Job Title, Company, Location, Shift, Type, Posted, Apply Link, Status.
    if not settings.tracker_csv_path:
        return []
    path = Path(settings.tracker_csv_path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if not row.get("Status", "").startswith("Skip")]
    return [to_posting(row) for row in rows[:limit]]


def to_posting(row: dict) -> Posting:
    location = row.get("Location", "")
    posted = row.get("Posted", "")
    notes = [row.get(key, "") for key in ("Track", "Shift", "Note") if row.get(key)]
    return Posting(
        source=NAME,
        external_id=row["Apply Link"],
        url=row["Apply Link"],
        apply_url=row["Apply Link"],
        title=row["Job Title"],
        company=row.get("Company", ""),
        locations=[location] if location else [],
        remote=location.lower() == "remote",
        employment_type=row.get("Type", ""),
        description=" | ".join(notes),
        posted_at=datetime.strptime(posted, "%Y-%m-%d") if posted else None,
    )
