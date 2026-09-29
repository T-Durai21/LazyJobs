import re

from ..models import Profile
from .base import Posting, client, html_to_text, parse_iso, polite_get

NAME = "remotive"
# Remotive's terms: link back to the Remotive URL, credit Remotive as the source, and fetch
# at most a few times a day. The registry's refresh floor enforces the last one.
FEED_URL = "https://remotive.com/api/remote-jobs"


def fetch(profile: Profile, limit: int) -> list[Posting]:
    with client() as http:
        jobs = polite_get(http, FEED_URL).json()["jobs"]
    return [to_posting(job) for job in jobs[:limit]]


def to_posting(job: dict) -> Posting:
    salary = job.get("salary") or ""
    return Posting(
        source=NAME,
        external_id=str(job["id"]),
        url=job["url"],
        apply_url=job["url"],
        title=job["title"],
        company=job.get("company_name", ""),
        locations=[part.strip() for part in (job.get("candidate_required_location") or "").split(",") if part.strip()],
        remote=True,
        employment_type=job.get("job_type", ""),
        description=html_to_text(job.get("description", "")),
        posted_at=parse_iso(job.get("publication_date")),
        salary_text=salary,
        salary_max_usd=usd_from_text(salary),
    )


def usd_from_text(text: str) -> float:
    # Remotive salary is free text such as "$60k - $80k" or "USD 90,000"; only USD is trusted.
    if "$" not in text and "usd" not in text.lower():
        return 0
    amounts = [
        float(number.replace(",", "")) * (1000 if suffix.lower() == "k" else 1)
        for number, suffix in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*(k?)", text, re.I)
    ]
    best = max(amounts, default=0)
    return best if best >= 1000 else 0
