"""
SQLAlchemy engine factory — Phase 8: connection pooling + pool event metrics.

Returns a single shared engine per process lifetime.
Supports SQLite (development/testing) and PostgreSQL (production).
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
        # PostgreSQL — configurable pool to avoid exhausting connections under load
        engine = create_engine(
            url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,   # discard stale connections transparently
            echo=False,
        )

        # Connection pool metrics (Phase 8)
        @event.listens_for(engine, "checkout")
        def _on_checkout(dbapi_conn, connection_record, connection_proxy):
            from backend.app.services.metrics_service import metrics
            metrics.increment("db:pool:checkouts")

    _engine = engine
    return _engine
