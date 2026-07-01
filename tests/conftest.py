"""
Shared pytest fixtures.

DB isolation strategy:
- Every test gets a fresh SQLite file in pytest's tmp_path.
- We monkeypatch src.database.DB_PATH (and its _connect function) so that
  all code paths — including backend.app.models.database which delegates
  to src.database._connect — automatically use the temp file.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.database as _core_db
import backend.app.models.database as _ext_db


# ── Database isolation ────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fresh SQLite file per test, with all tables already initialised."""
    db_file = tmp_path / "test.db"

    def _test_connect() -> sqlite3.Connection:
        db_file.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(db_file))

    monkeypatch.setattr(_core_db, "DB_PATH", db_file)
    monkeypatch.setattr(_core_db, "_connect", _test_connect)
    # _ext_db._connect delegates to _core_db._connect, so patching _core is sufficient
    _ext_db.init_all_tables()
    return db_file


# ── HTTP test client ──────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_db: Path) -> TestClient:
    """FastAPI TestClient wired to a fresh isolated database."""
    from backend.main import app
    # Re-run lifespan so init_all_tables() runs against the patched DB
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── Auth helpers ──────────────────────────────────────────────────────────────

@pytest.fixture()
def registered_user(client: TestClient) -> dict:
    """Register a test user and return {access_token, refresh_token, user}."""
    resp = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "Test1234",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    return {
        "user": data["user"],
        "access_token": data["tokens"]["access_token"],
        "refresh_token": data["tokens"]["refresh_token"],
    }


@pytest.fixture()
def auth_headers(registered_user: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {registered_user['access_token']}"}
