"""
Shared pytest fixtures.

DB isolation strategy (Phase 7+):
- Every test gets a fresh SQLite engine pointing at a temp file in pytest's tmp_path.
- We monkeypatch backend.app.models.db._engine so that all code paths that call
  get_engine() automatically use the isolated test database.
- The SQLite price-cache path (src.database) is patched separately so that any
  code path that calls get_prices() (always mocked at the service level) cannot
  accidentally write to the real data/ directory.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import backend.app.models.db as _db_module
import src.database as _src_db


# ── Database isolation ────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fresh SQLite engine per test, all tables initialised."""
    db_file = tmp_path / "test.db"

    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    # FK enforcement is left OFF in tests — unit tests use fake user IDs without
    # inserting real user rows. Production SQLite enables FK via the engine in db.py.

    # Point the backend DB module at the test engine
    monkeypatch.setattr(_db_module, "_engine", test_engine)

    # Keep the legacy price-cache path isolated too
    def _test_src_connect() -> sqlite3.Connection:
        return sqlite3.connect(str(db_file))

    monkeypatch.setattr(_src_db, "DB_PATH", db_file)
    monkeypatch.setattr(_src_db, "_connect", _test_src_connect)

    from backend.app.models.database import init_all_tables
    init_all_tables()
    return db_file


# ── HTTP test client ──────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_db: Path) -> TestClient:
    """FastAPI TestClient wired to a fresh isolated database."""
    from backend.main import app
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
