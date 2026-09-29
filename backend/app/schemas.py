from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cv_filename: str
    full_name: str
    headline: str
    summary: str
    titles: list[str]
    skills: list[str]
    years_experience: float
    preferred_locations: list[str]
    remote_only: bool
    min_salary: int
    extra_keywords: list[str]
    exclude_keywords: list[str]
    prefer_non_coding: bool


class ProfilePatch(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    titles: list[str] | None = None
    skills: list[str] | None = None
    years_experience: float | None = None
    preferred_locations: list[str] | None = None
    remote_only: bool | None = None
    min_salary: int | None = None
    extra_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    prefer_non_coding: bool | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    url: str
    apply_url: str
    title: str
    company: str
    locations: list[str]
    remote: bool
    employment_type: str
    posted_at: datetime | None
    salary_text: str
    salary_max_usd: float


class MatchOut(BaseModel):
    job: JobOut
    score: int
    reason: str
    application_id: int | None
    application_status: str | None


class ApplicationCreate(BaseModel):
    job_id: int
    draft_letter: bool = False


class ApplicationPatch(BaseModel):
    status: str | None = None
    notes: str | None = None
    cover_letter: str | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    score: float
    match_reason: str
    cover_letter: str
    notes: str
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    job: JobOut
