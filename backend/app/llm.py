import json
import re

import anthropic
from fastapi import HTTPException

from .config import settings
from .matching import SKILL_TERMS, normalise
from .models import Job, Profile

MAX_CV_CHARS = 60_000
MAX_JOB_CHARS = 12_000

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "full_name": {"type": "string"},
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "titles": {"type": "array", "items": {"type": "string"}},
        "skills": {"type": "array", "items": {"type": "string"}},
        "years_experience": {"type": "number"},
    },
    "required": ["full_name", "headline", "summary", "titles", "skills", "years_experience"],
    "additionalProperties": False,
}


def enabled() -> bool:
    return bool(settings.anthropic_api_key)


def _ask_claude(prompt: str, max_tokens: int, output_format: dict | None = None) -> str:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    output_config: dict = {"effort": "low"}
    if output_format:
        output_config["format"] = output_format
    try:
        response = client.beta.messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config=output_config,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.AuthenticationError as exc:
        raise HTTPException(status_code=502, detail="ANTHROPIC_API_KEY was rejected") from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(status_code=503, detail="Claude rate limit hit; try again shortly") from exc
    except anthropic.APIStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Claude API error {exc.status_code}") from exc
    except anthropic.APIConnectionError as exc:
        raise HTTPException(status_code=503, detail="Could not reach the Claude API") from exc
    if response.stop_reason == "refusal":
        raise HTTPException(status_code=502, detail="Claude declined this request")
    return "".join(block.text for block in response.content if block.type == "text")


def extract_profile(cv_text: str) -> dict:
    if not enabled():
        return _extract_profile_by_rules(cv_text)
    prompt = (
        "Extract a structured candidate profile from this CV. titles are job titles the person "
        "has held or is targeting; skills are concrete tools, technologies and methods; "
        "years_experience is total professional years excluding career breaks.\n\n<cv>\n"
        + cv_text[:MAX_CV_CHARS]
        + "\n</cv>"
    )
    text = _ask_claude(prompt, 4000, {"type": "json_schema", "schema": PROFILE_SCHEMA})
    return json.loads(text)


def draft_cover_letter(profile: Profile, job: Job, matched_skills: list[str]) -> str:
    if not enabled():
        return _cover_letter_template(profile, job, matched_skills)
    prompt = (
        "Write a short cover letter (150-220 words) for this candidate and job. Write in the "
        "language of the job posting. Name the company and role, lead with the experience most "
        "relevant to this posting, use only facts from the candidate profile, and end with "
        "availability. Plain text, no placeholders.\n\n"
        f"<candidate>\nName: {profile.full_name}\nHeadline: {profile.headline}\n"
        f"Summary: {profile.summary}\nTitles: {', '.join(profile.titles)}\n"
        f"Matched skills: {', '.join(matched_skills)}\n</candidate>\n\n"
        f"<job>\nCompany: {job.company}\nTitle: {job.title}\n"
        f"Description: {job.description[:MAX_JOB_CHARS]}\n</job>"
    )
    return _ask_claude(prompt, 2000).strip()


def _extract_profile_by_rules(cv_text: str) -> dict:
    # Without an API key the profile is a best-effort starting point the user corrects by hand.
    lines = [line.strip() for line in cv_text.splitlines() if line.strip()]
    text = normalise(cv_text)
    skills = [term for term in SKILL_TERMS if re.search(rf"(?<![a-z0-9]){re.escape(normalise(term))}(?![a-z0-9])", text)]
    years = re.search(r"(\d+(?:\.\d+)?)\+?\s*years", cv_text, re.I)
    headline = lines[1] if len(lines) > 1 else ""
    return {
        "full_name": lines[0].title() if lines else "",
        "headline": headline,
        "summary": " ".join(lines[2:6])[:800],
        "titles": [part.strip() for part in headline.split("|") if part.strip()],
        "skills": skills,
        "years_experience": float(years.group(1)) if years else 0,
    }


def _cover_letter_template(profile: Profile, job: Job, matched_skills: list[str]) -> str:
    skills = ", ".join(matched_skills[:6]) or ", ".join(profile.skills[:6])
    return (
        f"Dear {job.company} hiring team,\n\n"
        f"I am applying for the {job.title} role. {profile.summary[:400]}\n\n"
        f"The skills from my background that match this role most closely are {skills}. "
        f"I would welcome the chance to bring them to {job.company}.\n\n"
        "I am available to start immediately.\n\n"
        f"Regards,\n{profile.full_name}"
    )
