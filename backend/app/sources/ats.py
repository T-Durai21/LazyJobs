import logging
from datetime import datetime

import httpx

from ..models import Profile
from .base import Posting, annual_usd, client, html_to_text, parse_iso, polite_get
from .companies import WATCHLIST

NAME = "ats"
log = logging.getLogger(__name__)

BOARD_URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true",
}


def fetch(profile: Profile, limit: int) -> list[Posting]:
    postings: list[Posting] = []
    with client() as http:
        for provider, slug in WATCHLIST:
            try:
                data = polite_get(http, BOARD_URLS[provider].format(slug=slug)).json()
            except (httpx.HTTPError, ValueError) as exc:
                # One company renaming its board should not sink the whole refresh.
                log.warning("skipping %s/%s: %s", provider, slug, exc)
                continue
            postings += MAPPERS[provider](slug, data)
            if len(postings) >= limit:
                break
    return postings[:limit]


def is_remote(*texts: str) -> bool:
    return any("remote" in (text or "").lower() for text in texts)


def greenhouse(slug: str, data: dict) -> list[Posting]:
    result = []
    for job in data.get("jobs", []):
        location = (job.get("location") or {}).get("name", "")
        offices = [office["name"] for office in job.get("offices") or [] if office.get("name")]
        result.append(Posting(
            source=NAME,
            external_id=f"greenhouse:{slug}:{job['id']}",
            url=job["absolute_url"],
            apply_url=job["absolute_url"],
            title=job["title"],
            company=job.get("company_name") or slug,
            locations=[location, *offices] if location else offices,
            remote=is_remote(location),
            employment_type="",
            description=html_to_text(job.get("content", "")),
            posted_at=parse_iso(job.get("first_published") or job.get("updated_at")),
        ))
    return result


def lever(slug: str, data: list) -> list[Posting]:
    result = []
    for job in data:
        categories = job.get("categories") or {}
        locations = categories.get("allLocations") or [categories.get("location", "")]
        created = job.get("createdAt")
        result.append(Posting(
            source=NAME,
            external_id=f"lever:{slug}:{job['id']}",
            url=job["hostedUrl"],
            apply_url=job.get("applyUrl") or job["hostedUrl"],
            title=job["text"],
            company=slug.title(),
            locations=[place for place in locations if place],
            remote=job.get("workplaceType") == "remote" or is_remote(*locations),
            employment_type=categories.get("commitment", ""),
            description=f"{job.get('descriptionPlain', '')}\n{job.get('additionalPlain', '')}",
            posted_at=datetime.utcfromtimestamp(created / 1000) if created else None,
        ))
    return result


def ashby(slug: str, data: dict) -> list[Posting]:
    result = []
    for job in data.get("jobs", []):
        if not job.get("isListed", True):
            continue
        places = [job.get("location", ""), *[s.get("location", "") for s in job.get("secondaryLocations") or []]]
        salary_text, salary_usd = ashby_salary(job.get("compensation") or {})
        result.append(Posting(
            source=NAME,
            external_id=f"ashby:{slug}:{job['id']}",
            url=job["jobUrl"],
            apply_url=job.get("applyUrl") or job["jobUrl"],
            title=job["title"],
            company=slug.title(),
            locations=[place for place in places if place],
            remote=bool(job.get("isRemote")) or job.get("workplaceType") == "Remote",
            employment_type=job.get("employmentType", ""),
            description=job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml", "")),
            posted_at=parse_iso(job.get("publishedAt")),
            salary_text=salary_text,
            salary_max_usd=salary_usd,
        ))
    return result


def ashby_salary(compensation: dict) -> tuple[str, float]:
    best = 0.0
    for tier in compensation.get("summaryComponents") or []:
        if tier.get("compensationType") != "Salary":
            continue
        interval = (tier.get("interval") or "1 YEAR").split()[-1].lower()
        best = max(best, annual_usd(float(tier.get("maxValue") or 0), tier.get("currencyCode", ""), interval))
    return compensation.get("compensationTierSummary") or "", best


MAPPERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby}
