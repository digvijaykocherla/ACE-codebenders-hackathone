"""API tests. Each test gets a fresh temporary SQLite file via the get_db override."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  (registers tables)
from app.database import Base, get_db
from app.main import app

PASSWORD = "Demo@1234"


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # No `with` block: lifespan (which would create tables in the real DB) is skipped on purpose.
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


def _register(client, email: str, name: str) -> str:
    r = client.post("/api/auth/register", json={
        "full_name": name, "email": email, "password": PASSWORD, "city": "Pune"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_circle(client, token: str) -> int:
    r = client.post("/api/care-recipients", headers=_auth(token), json={"full_name": "Test Parent (SYNTHETIC)", "city": "Pune"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_register_and_login(client):
    _register(client, "a@test.dev", "Asha")
    r = client.post("/api/auth/login", json={"email": "a@test.dev", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["access_token"]
    assert body["user"]["email"] == "a@test.dev"
    assert client.post("/api/auth/login", json={"email": "a@test.dev", "password": "wrong-pass"}).status_code == 401


def test_unauthenticated_request_is_rejected(client):
    r = client.get("/api/care-recipients")
    assert r.status_code in (401, 403)


def test_viewer_cannot_write_tasks(client):
    owner = _register(client, "owner@test.dev", "Owner")
    viewer = _register(client, "viewer@test.dev", "Viewer")
    rid = _create_circle(client, owner)
    r = client.post(f"/api/care-recipients/{rid}/members", headers=_auth(owner),
                    json={"email": "viewer@test.dev", "role": "viewer"})
    assert r.status_code == 201, r.text
    r = client.post(f"/api/care-recipients/{rid}/tasks", headers=_auth(viewer), json={"title": "Call pharmacy"})
    assert r.status_code == 403


def test_non_member_gets_404(client):
    owner = _register(client, "own2@test.dev", "Owner")
    stranger = _register(client, "stranger@test.dev", "Stranger")
    rid = _create_circle(client, owner)
    r = client.get(f"/api/care-recipients/{rid}", headers=_auth(stranger))
    assert r.status_code == 404


def test_timeline_returns_all_three_item_types(client):
    token = _register(client, "tl@test.dev", "Timeline")
    rid = _create_circle(client, token)
    future = (datetime.now() + timedelta(days=30)).isoformat()
    base = f"/api/care-recipients/{rid}"
    assert client.post(f"{base}/appointments", headers=_auth(token),
                       json={"title": "Check-up", "scheduled_at": future}).status_code == 201
    assert client.post(f"{base}/prescriptions", headers=_auth(token),
                       json={"medicine_name": "Test Med", "dosage_text": "1 daily",
                             "start_date": "2024-01-01", "refills_remaining": 2}).status_code == 201
    assert client.post(f"{base}/reports", headers=_auth(token),
                       json={"title": "Panel", "report_type": "lab", "report_date": "2024-02-01"}).status_code == 201

    r = client.get(f"{base}/timeline", headers=_auth(token))
    assert r.status_code == 200
    types = {item["item_type"] for item in r.json()}
    assert types == {"appointment", "prescription", "report"}
