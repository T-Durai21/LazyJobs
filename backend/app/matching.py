import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache

from .models import Job, Profile

SKILL_TERMS = [
    "Python", "Java", "JavaScript", "TypeScript", "SQL", "Dart", "HTML", "CSS",
    "Selenium", "TestNG", "Playwright", "Cypress", "Appium", "Postman", "REST API", "API Testing",
    "Manual Testing", "Regression Testing", "Functional Testing", "Integration Testing", "UAT",
    "Test Cases", "Test Automation", "JIRA", "Agile", "Scrum", "Git", "Maven", "Page Object Model",
    "Generative AI", "GenAI", "LLM", "Prompt Engineering", "LLM Evaluation", "Evaluation",
    "Claude", "OpenAI", "RAG", "LangChain", "Agentic", "Machine Learning", "NLP",
    "Flutter", "Android", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Linux",
    "Requirements", "Business Analysis", "Stakeholder", "Documentation", "Technical Writing",
    "Data Analysis", "Excel", "Power BI", "Tableau", "Banking", "Payments", "UPI", "Healthcare",
    "Insurance", "Fintech", "Customer Success", "Implementation", "Onboarding",
    "Red Teaming", "Adversarial Testing", "Data Annotation", "Data Labeling", "AI Safety", "Trust and Safety",
    "Business Analyst", "Product Analyst", "AI QA", "Model Evaluation",
]

# Titles that mean writing production code for a living. Anything else (analyst, QA analyst,
# consultant, writer, specialist, manager) counts as non-coding for the preference boost.
CODING_TITLE_TERMS = [
    "developer", "software engineer", "sde", "sdet", "programmer", "full stack", "fullstack",
    "backend", "back end", "frontend", "front end", "devops", "ml engineer", "machine learning engineer",
    "ai engineer", "data engineer", "platform engineer", "site reliability", "architect",
    "automation engineer", "mobile engineer", "ios engineer", "android engineer",
]

# Words that appear in most titles and say nothing about the kind of work.
GENERIC_TITLE_WORDS = {
    "engineer", "senior", "sr", "staff", "lead", "principal", "manager", "specialist", "associate",
    "junior", "jr", "i", "ii", "iii", "iv", "and", "the", "of", "for", "with", "remote", "global",
    "data", "red",
}
# A posting must hit a target title or this many skills, or it is noise however well it pays.
MIN_SKILLS_WITHOUT_TITLE = 5

# Countries whose currency is worth at least about 0.6 USD, strongest first. A job based
# there usually pays in that currency, so it is worth ranking above a local-currency role.
STRONG_CURRENCY_PLACES = [
    "kuwait", "bahrain", "oman", "jordan", "united kingdom", "uk", "london", "switzerland", "zurich",
    "cayman", "germany", "netherlands", "ireland", "france", "europe", "emea", "united states", "usa",
    "singapore", "canada", "australia", "new zealand", "uae", "dubai", "saudi", "qatar",
]

WORLDWIDE_TERMS = ["worldwide", "anywhere", "global", "remote - any"]

SYNONYMS = {
    "genai": "generative ai",
    "gen ai": "generative ai",
    "large language model": "llm",
    "quality assurance": "qa",
    "user acceptance testing": "uat",
    "restful": "rest api",
}


def normalise(text: str) -> str:
    stripped = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    lowered = stripped.lower()
    for phrase, canonical in SYNONYMS.items():
        lowered = lowered.replace(phrase, canonical)
    return re.sub(r"\s+", " ", lowered)


# Terms are a few hundred short strings reused across every posting, so their normalised
# forms are cached; ranking thousands of postings spent most of its time re-normalising them.
@lru_cache(maxsize=4096)
def term_key(term: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", normalise(term)))


def contains_term(text: str, term: str) -> bool:
    return f" {term_key(term)} " in short_word_text(text)


def word_text(text: str) -> str:
    return " " + " ".join(re.findall(r"[a-z0-9]+", normalise(text))) + " "


# Only titles, employment types and location lists come through here, never descriptions,
# so the cache stays small while each is checked against dozens of terms.
@lru_cache(maxsize=16384)
def short_word_text(text: str) -> str:
    return word_text(text)


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalise(text))


# Requirements sit near the top of a posting; the tail is benefits and legal boilerplate.
DESCRIPTION_CHARS_SCANNED = 8000


def is_coding_role(title: str) -> bool:
    text = normalise(title)
    return any(contains_term(text, term) for term in CODING_TITLE_TERMS)


@dataclass
class Match:
    job: Job
    score: int
    reason: str
    matched_skills: list[str] = field(default_factory=list)
    relevant: bool = True


def rejection(job: Job, profile: Profile) -> str | None:
    title = normalise(job.title)
    kind = normalise(job.employment_type)
    for word in profile.exclude_keywords:
        if contains_term(title, word) or contains_term(kind, word):
            return f"excluded keyword: {word}"
    if profile.remote_only and not job.remote:
        return "not remote"
    if profile.min_salary and job.salary_max_usd and job.salary_max_usd < profile.min_salary:
        return "salary below minimum"
    if not location_ok(job, profile):
        return "location"
    return None


def location_ok(job: Job, profile: Profile) -> bool:
    wanted = [normalise(place) for place in profile.preferred_locations if place.strip()]
    places = [normalise(place) for place in job.locations]
    if not wanted:
        return True
    # For remote postings the locations list is who may apply, so an empty list means anyone.
    if job.remote and not places:
        return True
    if any(term in place for place in places for term in WORLDWIDE_TERMS):
        return True
    return any(w in place for w in wanted for place in places)


def score(job: Job, profile: Profile, now: datetime) -> Match:
    index = word_text(f"{job.title} {job.description[:DESCRIPTION_CHARS_SCANNED]}")
    title = normalise(job.title)

    wanted_skills = list(dict.fromkeys(profile.skills + profile.extra_keywords))
    matched = [skill for skill in wanted_skills if f" {term_key(skill)} " in index]
    skill_points = 40 * min(len(matched), 8) / 8 if wanted_skills else 0

    title_points = title_score(title, profile.titles)

    recency_points = 0
    if job.posted_at:
        age_days = (now - job.posted_at).days
        recency_points = 10 if age_days <= 7 else 5 if age_days <= 30 else 0

    salary_points = 10 if job.salary_max_usd >= 30_000 else 5 if job.salary_max_usd >= 15_000 else 0
    remote_points = 5 if job.remote else 0
    strong_currency = in_strong_currency_place(job)
    currency_points = 10 if strong_currency else 0

    coding = is_coding_role(job.title)
    preference_points = 0
    if profile.prefer_non_coding:
        preference_points = -15 if coding else 10

    total = skill_points + title_points + recency_points + salary_points + remote_points + currency_points + preference_points
    return Match(
        job=job,
        score=max(0, min(100, round(total))),
        reason=build_reason(matched, len(wanted_skills), job, coding, profile.prefer_non_coding, strong_currency),
        matched_skills=matched,
        relevant=title_points > 0 or len(matched) >= MIN_SKILLS_WITHOUT_TITLE,
    )


def title_score(title: str, targets: list[str]) -> float:
    if any(contains_term(title, target) for target in targets if target.strip()):
        return 30
    distinctive = {w for t in targets for w in normalise(t).split()} - GENERIC_TITLE_WORDS
    shared = distinctive & set(re.findall(r"[a-z0-9]+", title))
    return min(len(shared), 2) * 12


def place_tier(job: Job) -> int:
    # Ordering before score: strong-currency countries, then open or worldwide roles, then
    # roles based only in India, which pay in rupees whatever the score says.
    if in_strong_currency_place(job):
        return 0
    places = normalise(" ; ".join(job.locations))
    if places and contains_term(places, "india") and not any(term in places for term in WORLDWIDE_TERMS):
        return 2
    return 1


def in_strong_currency_place(job: Job) -> bool:
    places = normalise(" ; ".join(job.locations))
    return any(contains_term(places, place) for place in STRONG_CURRENCY_PLACES)


def build_reason(
    matched: list[str], wanted: int, job: Job, coding: bool, prefer_non_coding: bool, strong_currency: bool
) -> str:
    parts = []
    if matched:
        parts.append(f"matches {len(matched)} of your {wanted} skills: {', '.join(matched[:6])}")
    else:
        parts.append("no skill overlap found in the description")
    if job.salary_text:
        parts.append(f"pay: {job.salary_text}")
    if job.remote:
        parts.append("remote")
    if strong_currency:
        parts.append("strong-currency country")
    if prefer_non_coding:
        parts.append("coding role" if coding else "non-coding role")
    return "; ".join(parts)


def rank(jobs: list[Job], profile: Profile, now: datetime) -> list[Match]:
    kept = [job for job in jobs if rejection(job, profile) is None]
    scored = (score(job, profile, now) for job in kept)
    # Large global employers first within each place tier: the company-board watchlist is
    # made up of them, and they pay far above the local market.
    return sorted(
        (m for m in scored if m.relevant),
        key=lambda m: (
            place_tier(m.job),
            m.job.source != "ats",
            profile.prefer_non_coding and is_coding_role(m.job.title),
            -m.score,
        ),
    )
