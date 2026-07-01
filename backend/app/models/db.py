"""
SQLAlchemy engine factory.

Returns a single shared engine for the process lifetime.
Supports SQLite (development / testing) and PostgreSQL (production).
Tests override `_engine` via monkeypatch before calling init_all_tables().
"""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    from backend.app.core.config import settings

    url = settings.database_url
    # Accept bare file paths for SQLite (e.g. "data/portfolio.db")
    if not any(url.startswith(s) for s in ("sqlite:", "postgresql:", "postgres:")):
        url = f"sqlite:///{url}"

    if url.startswith("sqlite:"):
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA journal_mode=WAL")
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    else:
        engine = create_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False,
        )

    _engine = engine
    return _engine
