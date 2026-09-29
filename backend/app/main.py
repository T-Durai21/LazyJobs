from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers.applications import router as applications_router
from .routers.auth import router as auth_router
from .routers.jobs import router as jobs_router
from .routers.profile import router as profile_router

# The schema is owned by Alembic: run `alembic upgrade head` before starting the app.
app = FastAPI(title="CV Applier")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(jobs_router)
app.include_router(applications_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Mounted last so every /api route above wins over the static catch-all.
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
