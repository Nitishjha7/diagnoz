"""Integration test fixtures. These tests run against the REAL Docker Compose stack
(real Postgres+PostGIS, real Redis) - the same philosophy as eval/run_eval.py. No mocks,
because the bugs that matter here (FK direction, PostGIS query correctness, Redis lock
races) only show up against real infrastructure.

Run with: docker compose exec backend pytest tests/ -v
"""
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app

DELHI_LAT, DELHI_LON = 28.6139, 77.2090


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def unique_suffix() -> str:
    return uuid.uuid4().hex[:10]


@pytest.fixture
def register_user(client):
    """Factory fixture: register_user(role="CUSTOMER") -> (user_dict, password)."""

    def _register(role="CUSTOMER", full_name=None):
        suffix = unique_suffix()
        password = "testpass123"
        payload = {
            "full_name": full_name or f"Test {role.title()} {suffix}",
            "email": f"test_{suffix}@example.com",
            "phone_number": f"9{int(time.time() * 1000) % 10**9:09d}",
            "password": password,
            "role": role,
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201, resp.text
        return resp.json(), password

    return _register


@pytest.fixture
def login(client):
    """Factory fixture: login(email, password) -> access_token."""

    def _login(email, password):
        resp = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    return _login


@pytest.fixture
def auth_headers(login):
    def _headers(email, password):
        token = login(email, password)
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture
def customer(client, register_user, auth_headers):
    """A registered+logged-in CUSTOMER: returns (user, headers)."""
    user, password = register_user(role="CUSTOMER")
    headers = auth_headers(user["email"], password)
    return user, headers


@pytest.fixture
def technician(client, register_user, auth_headers):
    """A registered+logged-in TECHNICIAN: returns (user, headers)."""
    user, password = register_user(role="TECHNICIAN")
    headers = auth_headers(user["email"], password)
    return user, headers


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def available_technician(client, technician, db_session):
    """A logged-in technician with a saved profile at a known location, and every OTHER
    technician in the DB temporarily marked unavailable so KNN dispatch tests are
    deterministic regardless of what demo/other-test data already exists - same isolation
    approach as eval/run_eval.py's dispatch eval.
    """
    user, headers = technician
    resp = client.post(
        "/api/v1/technicians/me/profile",
        json={"latitude": DELHI_LAT, "longitude": DELHI_LON},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    profile_id = resp.json()["id"]

    other_ids = [
        row[0]
        for row in db_session.execute(
            text("SELECT id FROM technician_profiles WHERE is_available = TRUE AND id != :id"),
            {"id": profile_id},
        ).fetchall()
    ]
    if other_ids:
        db_session.execute(
            text("UPDATE technician_profiles SET is_available = FALSE WHERE id = ANY(:ids)"),
            {"ids": other_ids},
        )
        db_session.commit()

    yield user, headers

    if other_ids:
        db_session.execute(
            text("UPDATE technician_profiles SET is_available = TRUE WHERE id = ANY(:ids)"),
            {"ids": other_ids},
        )
        db_session.commit()
