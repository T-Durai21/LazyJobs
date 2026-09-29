import html
import re
import time
from dataclasses import dataclass
from datetime import datetime

import httpx

from ..config import settings


@dataclass
class Posting:
    source: str
    external_id: str
    url: str
    apply_url: str
    title: str
    company: str
    locations: list[str]
    remote: bool
    employment_type: str
    description: str
    posted_at: datetime | None
    salary_text: str = ""
    salary_max_usd: float = 0


# Rough rates, good enough to rank postings against each other; not for quoting pay.
USD_PER_UNIT = {
    "KWD": 3.24, "BHD": 2.65, "OMR": 2.59, "JOD": 1.41, "GBP": 1.35, "CHF": 1.24, "EUR": 1.15,
    "USD": 1.0, "SGD": 0.74, "CAD": 0.73, "AUD": 0.67, "NZD": 0.60,
    "AED": 0.27, "SAR": 0.27, "QAR": 0.27, "INR": 1 / 83,
}
PERIODS_PER_YEAR = {"year": 1, "yearly": 1, "annual": 1, "month": 12, "monthly": 12, "hour": 2080, "hourly": 2080}


def annual_usd(amount: float, currency: str, period: str) -> float:
    rate = USD_PER_UNIT.get((currency or "USD").upper())
    per_year = PERIODS_PER_YEAR.get((period or "year").lower())
    if not amount or rate is None or per_year is None:
        return 0
    return round(amount * rate * per_year)


def html_to_text(raw: str) -> str:
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", html.unescape(raw or ""), flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", html.unescape(text)).strip()


def client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": settings.user_agent}, timeout=30, follow_redirects=True)


def polite_get(http: httpx.Client, url: str) -> httpx.Response:
    time.sleep(settings.source_request_delay)
    response = http.get(url)
    response.raise_for_status()
    return response


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
