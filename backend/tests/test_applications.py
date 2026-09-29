import os
import tempfile

db_file = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
os.environ["LOCAL_LOGIN_EMAIL"] = "tester@example.com"
os.environ["ANTHROPIC_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Job  # noqa: E402


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(Job(source="test", external_id="1", url="https://x", apply_url="https://x",
                   title="Business Analyst", company="Acme", locations=[], remote=True, description="UAT SQL"))
        db.commit()
    test_client = TestClient(app)
    assert test_client.post("/api/auth/local/login").status_code == 204
    return test_client


def test_lifecycle_and_submitted_at_stamped_once(client):
    app_id = client.post("/api/applications", json={"job_id": 1, "draft_letter": True}).json()["id"]
    assert client.get("/api/applications").json()[0]["status"] == "drafted"
    assert "Acme" in client.get("/api/applications").json()[0]["cover_letter"]

    first = client.patch(f"/api/applications/{app_id}", json={"status": "submitted"}).json()
    assert first["submitted_at"] is not None
    later = client.patch(f"/api/applications/{app_id}", json={"status": "interview"}).json()
    assert later["submitted_at"] == first["submitted_at"]
    assert [a["id"] for a in client.get("/api/applications?status=interview").json()] == [app_id]


def test_invalid_transition_rejected(client):
    app_id = client.post("/api/applications", json={"job_id": 1}).json()["id"]
    response = client.patch(f"/api/applications/{app_id}", json={"status": "submitted"})
    assert response.status_code == 409
    assert client.patch(f"/api/applications/{app_id}", json={"status": "bogus"}).status_code == 400


def test_duplicate_application_rejected(client):
    assert client.post("/api/applications", json={"job_id": 1}).status_code == 201
    assert client.post("/api/applications", json={"job_id": 1}).status_code == 409


def test_requires_sign_in():
    assert TestClient(app).get("/api/applications").status_code == 401
