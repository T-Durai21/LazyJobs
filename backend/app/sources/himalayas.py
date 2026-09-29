from datetime import datetime

from ..models import Profile
from .base import Posting, annual_usd, client, html_to_text, polite_get

NAME = "himalayas"
FEED_URL = "https://himalayas.app/jobs/api"
PAGE_SIZE = 20
MAX_PAGES = 10


def fetch(profile: Profile, limit: int) -> list[Posting]:
    postings: list[Posting] = []
    cursor = ""
    with client() as http:
        for _ in range(MAX_PAGES):
            url = f"{FEED_URL}?limit={PAGE_SIZE}" + (f"&cursor={cursor}" if cursor else "")
            page = polite_get(http, url).json()
            postings += [to_posting(job) for job in page.get("jobs", [])]
            cursor = page.get("nextCursor") or ""
            if not cursor or len(postings) >= limit:
                break
    return postings[:limit]


def to_posting(job: dict) -> Posting:
    currency = job.get("currency") or "USD"
    period = job.get("salaryPeriod") or "year"
    high = float(job.get("maxSalary") or job.get("minSalary") or 0)
    low = float(job.get("minSalary") or 0)
    salary_text = f"{currency} {low:,.0f}-{high:,.0f} per {period}" if high else ""
    published = job.get("pubDate")
    return Posting(
        source=NAME,
        external_id=job["guid"],
        url=job["guid"],
        apply_url=job.get("applicationLink") or job["guid"],
        title=job["title"],
        company=job.get("companyName", ""),
        # An empty restriction list means the role is open worldwide.
        locations=list(job.get("locationRestrictions") or []),
        remote=True,
        employment_type=job.get("employmentType", ""),
        description=html_to_text(job.get("description", "")),
        posted_at=datetime.utcfromtimestamp(int(published)) if published else None,
        salary_text=salary_text,
        salary_max_usd=annual_usd(high, currency, period),
    )
