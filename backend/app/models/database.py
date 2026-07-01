"""
Database layer — Phase 7+.
Supports SQLite (development) and PostgreSQL (production) via SQLAlchemy 2.0.
All schema creation and CRUD operations are self-contained here.
The legacy src/database.py price-cache path is left unchanged.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    delete,
    insert,
    select,
    update,
)

from backend.app.models.db import get_engine

metadata = MetaData()

# ── Schema ────────────────────────────────────────────────────────────────────

users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("email", String(255), nullable=False, unique=True),
    Column("password_hash", Text, nullable=False),
    Column("created_at", String(50), nullable=False),
    Column("updated_at", String(50), nullable=False),
    Column("is_active", Integer, nullable=False, server_default="1"),
)

refresh_tokens_table = Table(
    "refresh_tokens",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("token_hash", Text, nullable=False, unique=True),
    Column("expires_at", String(50), nullable=False),
    Column("created_at", String(50), nullable=False),
    Column("is_revoked", Integer, nullable=False, server_default="0"),
)

audit_logs_table = Table(
    "audit_logs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=True),
    Column("action", String(100), nullable=False),
    Column("details", Text, nullable=True),
    Column("ip_address", String(50), nullable=True),
    Column("created_at", String(50), nullable=False),
)

portfolios_table = Table(
    "portfolios",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=True),
    Column("created_at", String(50), nullable=False),
    Column("tickers", Text, nullable=False),
    Column("start_date", String(20), nullable=False),
    Column("end_date", String(20), nullable=False),
    Column("expected_return", Float, nullable=False),
    Column("volatility", Float, nullable=False),
    Column("sharpe", Float, nullable=False),
    Column("basket_return", Float, nullable=True),
    Column("nifty_return", Float, nullable=True),
    Column("max_weight", Float, nullable=False),
    Column("num_portfolios", Integer, nullable=False, server_default="0"),
)

portfolio_weights_table = Table(
    "portfolio_weights",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "portfolio_id",
        Integer,
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("ticker", String(20), nullable=False),
    Column("weight", Float, nullable=False),
)

# Price-cache table — mirrored here so init_all_tables() is the single source
# of truth for all tables. The legacy src/database.py also creates this table;
# CREATE TABLE IF NOT EXISTS makes both coexist safely.
prices_table = Table(
    "prices",
    metadata,
    Column("ticker", String(20), primary_key=True, nullable=False),
    Column("date", String(20), primary_key=True, nullable=False),
    Column("close", Float, nullable=False),
    Column("last_updated", String(50), nullable=False),
)

# Phase 8 — async job tracking (persisted alongside Redis for durability)
jobs_table = Table(
    "jobs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=True),
    Column("status", String(20), nullable=False, server_default="queued"),
    Column("job_type", String(50), nullable=False, server_default="optimize"),
    Column("created_at", String(50), nullable=False),
    Column("started_at", String(50), nullable=True),
    Column("completed_at", String(50), nullable=True),
    Column("result", Text, nullable=True),
    Column("error", Text, nullable=True),
    Column("idempotency_key", String(64), nullable=True, unique=False),
)


# ── Initialisation ────────────────────────────────────────────────────────────


def init_all_tables() -> None:
    """Create all tables. Safe to call repeatedly (CREATE TABLE IF NOT EXISTS)."""
    metadata.create_all(get_engine())


# ── User CRUD ─────────────────────────────────────────────────────────────────


def create_user(name: str, email: str, password_hash: str) -> dict:
    now = datetime.now(UTC).isoformat()
    with get_engine().connect() as conn:
        result = conn.execute(
            insert(users_table).values(
                name=name,
                email=email,
                password_hash=password_hash,
                created_at=now,
                updated_at=now,
            )
        )
        conn.commit()
        user_id = result.inserted_primary_key[0]
    return {
        "id": user_id,
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "created_at": now,
        "updated_at": now,
        "is_active": 1,
    }


def get_user_by_id(user_id: int) -> dict | None:
    with get_engine().connect() as conn:
        row = (
            conn.execute(select(users_table).where(users_table.c.id == user_id))
            .mappings()
            .fetchone()
        )
    return dict(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    with get_engine().connect() as conn:
        row = (
            conn.execute(select(users_table).where(users_table.c.email == email))
            .mappings()
            .fetchone()
        )
    return dict(row) if row else None


# ── Refresh token CRUD ────────────────────────────────────────────────────────


def save_refresh_token(user_id: int, token_hash: str, expires_at: datetime) -> None:
    now = datetime.now(UTC).isoformat()
    with get_engine().connect() as conn:
        conn.execute(
            insert(refresh_tokens_table).values(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at.isoformat(),
                created_at=now,
            )
        )
        conn.commit()


def get_refresh_token(token_hash: str) -> dict | None:
    with get_engine().connect() as conn:
        row = (
            conn.execute(
                select(refresh_tokens_table).where(refresh_tokens_table.c.token_hash == token_hash)
            )
            .mappings()
            .fetchone()
        )
    return dict(row) if row else None


def revoke_refresh_token(token_hash: str) -> None:
    with get_engine().connect() as conn:
        conn.execute(
            update(refresh_tokens_table)
            .where(refresh_tokens_table.c.token_hash == token_hash)
            .values(is_revoked=1)
        )
        conn.commit()


def revoke_all_user_tokens(user_id: int) -> None:
    with get_engine().connect() as conn:
        conn.execute(
            update(refresh_tokens_table)
            .where(refresh_tokens_table.c.user_id == user_id)
            .values(is_revoked=1)
        )
        conn.commit()


# ── Audit log ─────────────────────────────────────────────────────────────────


def log_audit(
    user_id: int | None,
    action: str,
    details: str | None = None,
    ip: str | None = None,
) -> None:
    now = datetime.now(UTC).isoformat()
    with get_engine().connect() as conn:
        conn.execute(
            insert(audit_logs_table).values(
                user_id=user_id,
                action=action,
                details=details,
                ip_address=ip,
                created_at=now,
            )
        )
        conn.commit()


# ── Portfolio CRUD (with user ownership) ─────────────────────────────────────


def save_portfolio_for_user(
    user_id: int,
    tickers,
    start_date: str,
    end_date: str,
    expected_return: float,
    volatility: float,
    sharpe: float,
    basket_return: float | None,
    nifty_return: float | None,
    max_weight: float,
    num_portfolios: int,
    weights: dict,
) -> int:
    """Insert a portfolio row and its weights; returns the new portfolio ID."""
    now = datetime.now(UTC).isoformat()
    with get_engine().connect() as conn:
        result = conn.execute(
            insert(portfolios_table).values(
                user_id=user_id,
                created_at=now,
                tickers=json.dumps(sorted(tickers)),
                start_date=start_date,
                end_date=end_date,
                expected_return=float(expected_return),
                volatility=float(volatility),
                sharpe=float(sharpe),
                basket_return=float(basket_return) if basket_return is not None else None,
                nifty_return=float(nifty_return) if nifty_return is not None else None,
                max_weight=float(max_weight),
                num_portfolios=int(num_portfolios),
            )
        )
        portfolio_id = result.inserted_primary_key[0]

        weight_rows = [
            {"portfolio_id": portfolio_id, "ticker": t, "weight": float(w)}
            for t, w in weights.items()
            if w > 0
        ]
        if weight_rows:
            conn.execute(insert(portfolio_weights_table), weight_rows)

        conn.commit()
    return portfolio_id


def load_portfolio_history_for_user(user_id: int) -> list[dict]:
    """Return portfolios owned by this user, newest first."""
    with get_engine().connect() as conn:
        rows = (
            conn.execute(
                select(portfolios_table)
                .where(portfolios_table.c.user_id == user_id)
                .order_by(portfolios_table.c.created_at.desc())
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


def load_portfolio_by_id(portfolio_id: int) -> dict | None:
    with get_engine().connect() as conn:
        row = (
            conn.execute(select(portfolios_table).where(portfolios_table.c.id == portfolio_id))
            .mappings()
            .fetchone()
        )
    return dict(row) if row else None


def load_portfolio_weights(portfolio_id: int) -> dict[str, float]:
    with get_engine().connect() as conn:
        rows = conn.execute(
            select(portfolio_weights_table.c.ticker, portfolio_weights_table.c.weight)
            .where(portfolio_weights_table.c.portfolio_id == portfolio_id)
            .order_by(portfolio_weights_table.c.weight.desc())
        ).fetchall()
    return {row[0]: float(row[1]) for row in rows}


def get_portfolio_owner(portfolio_id: int) -> int | None:
    with get_engine().connect() as conn:
        row = conn.execute(
            select(portfolios_table.c.user_id).where(portfolios_table.c.id == portfolio_id)
        ).fetchone()
    return row[0] if row else None


def delete_portfolio(portfolio_id: int) -> bool:
    with get_engine().connect() as conn:
        conn.execute(
            delete(portfolio_weights_table).where(
                portfolio_weights_table.c.portfolio_id == portfolio_id
            )
        )
        result = conn.execute(delete(portfolios_table).where(portfolios_table.c.id == portfolio_id))
        conn.commit()
    return result.rowcount > 0
