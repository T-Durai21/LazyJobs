# CV Applier

A personal job-search assistant: parse a CV, match openings from global employers and
remote job boards, draft cover letters, and track applications. This fork
(T-Durai21/LazyJobs) runs locally only and targets a candidate in India looking for
well-paid roles abroad or remote; see [LEARNING.md](LEARNING.md) entry 27.

## Stack

- Backend: FastAPI, SQLAlchemy 2, Alembic, in `backend/`
- Frontend: one static page, `backend/app/static/index.html`, served by FastAPI at `/`.
  No build step. (The React plan in PLAN.md section 12 is deferred.)
- Auth: Google OpenID Connect, plus a local sign-in for one's own machine
  (`LOCAL_LOGIN_EMAIL`). Accounts are an email plus `identities` rows; no password column.
- LLM: Claude via the Anthropic SDK when `ANTHROPIC_API_KEY` is set; rules and a template
  otherwise.
- Database: SQLite locally; the schema is owned by Alembic.

## Running it (Windows paths shown)

```
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env        # set LOCAL_LOGIN_EMAIL, optionally TRACKER_CSV_PATH and ANTHROPIC_API_KEY
.venv\Scripts\alembic upgrade head
.venv\Scripts\uvicorn app.main:app --port 8000
```

Open `http://localhost:8000`, sign in, upload a CV on Profile, then Fetch new jobs on
Matches (the first fetch takes about two minutes). OpenAPI: `http://localhost:8000/docs`.

Schema changes: edit `app/models.py`, then
`.venv\Scripts\alembic revision --autogenerate -m "..."` and `alembic upgrade head`.

Tests: `.venv\Scripts\python -m pytest -q` from `backend/`.

## Cloud

Nothing is deployed and nothing is billed. The cloud design is in [PLAN.md](PLAN.md)
section 4 and [BUILD.md](BUILD.md) phases 4 and 12 to 15; those phases are deferred in
this fork.

## Docs

Subsystem docs live in `docs/` and are written in the same change as the code they
describe.

- [Authentication](docs/auth.md)
- [Job sources](docs/sources.md)
- [Matching](docs/matching.md)
- [Profile, CV parsing and the LLM](docs/profile-and-llm.md)
- [Applications and the frontend](docs/applications.md)
- Design: [PLAN.md](PLAN.md)
- Phase checklist: [BUILD.md](BUILD.md)
- Live phase status: [PROGRESS.md](PROGRESS.md)
- Why the code looks like this: [LEARNING.md](LEARNING.md)
