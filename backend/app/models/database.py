"""
Extended database layer for Phase 5.
Adds: users, refresh_tokens, audit_logs tables.
Migrates: portfolios ← user_id column.
Original prices / portfolios / portfolio_weights tables are managed by src.database.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import src.database as _core

DB_PATH = _core.DB_PATH


def _connect() -> sqlite3.Connection:
    return _core._connect()


def init_all_tables() -> None:
    """Create all tables (original + Phase 5). Safe to call repeatedly."""
    _core.create_tables()

    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                email         TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL,
                updated_at    TEXT    NOT NULL,
                is_active     INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash  TEXT    NOT NULL UNIQUE,
                expires_at  TEXT    NOT NULL,
                created_at  TEXT    NOT NULL,
                is_revoked  INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER REFERENCES users(id),
                action     TEXT    NOT NULL,
                details    TEXT,
                ip_address TEXT,
                created_at TEXT    NOT NULL
            );
        """)

        # Migrate: add user_id to portfolios if not present
        cols = {row[1] for row in conn.execute("PRAGMA table_info(portfolios)").fetchall()}
        if "user_id" not in cols:
            conn.execute("ALTER TABLE portfolios ADD COLUMN user_id INTEGER REFERENCES users(id)")


# ── User CRUD ─────────────────────────────────────────────────────────────────

def create_user(name: str, email: str, password_hash: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at, updated_at) VALUES (?,?,?,?,?)",
            (name, email, password_hash, now, now),
        )
        user_id = cur.lastrowid
    # Build the row without re-querying (INSERT is inside a transaction; second connection can't see it until commit)
    return {"id": user_id, "name": name, "email": email, "password_hash": password_hash,
            "created_at": now, "updated_at": now, "is_active": 1}


def get_user_by_id(user_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, name, email, password_hash, created_at, updated_at, is_active FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    keys = ["id", "name", "email", "password_hash", "created_at", "updated_at", "is_active"]
    return dict(zip(keys, row))


def get_user_by_email(email: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, name, email, password_hash, created_at, updated_at, is_active FROM users WHERE email=?",
            (email,),
        ).fetchone()
    if not row:
        return None
    keys = ["id", "name", "email", "password_hash", "created_at", "updated_at", "is_active"]
    return dict(zip(keys, row))


# ── Refresh token CRUD ────────────────────────────────────────────────────────

def save_refresh_token(user_id: int, token_hash: str, expires_at: datetime) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_at) VALUES (?,?,?,?)",
            (user_id, token_hash, expires_at.isoformat(), now),
        )


def get_refresh_token(token_hash: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, user_id, token_hash, expires_at, is_revoked FROM refresh_tokens WHERE token_hash=?",
            (token_hash,),
        ).fetchone()
    if not row:
        return None
    keys = ["id", "user_id", "token_hash", "expires_at", "is_revoked"]
    return dict(zip(keys, row))


def revoke_refresh_token(token_hash: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE refresh_tokens SET is_revoked=1 WHERE token_hash=?", (token_hash,))


def revoke_all_user_tokens(user_id: int) -> None:
    with _connect() as conn:
        conn.execute("UPDATE refresh_tokens SET is_revoked=1 WHERE user_id=?", (user_id,))


# ── Audit log ─────────────────────────────────────────────────────────────────

def log_audit(user_id: int | None, action: str, details: str | None = None, ip: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO audit_logs (user_id, action, details, ip_address, created_at) VALUES (?,?,?,?,?)",
            (user_id, action, details, ip, now),
        )


# ── Portfolio with ownership ──────────────────────────────────────────────────

def save_portfolio_for_user(user_id: int, **kwargs) -> int:
    """Delegate to src.database.save_portfolio then stamp user_id."""
    portfolio_id = _core.save_portfolio(**kwargs)
    with _connect() as conn:
        conn.execute("UPDATE portfolios SET user_id=? WHERE id=?", (user_id, portfolio_id))
    return portfolio_id


def load_portfolio_history_for_user(user_id: int):
    """Return portfolios owned by this user, newest first."""
    import pandas as pd
    with _connect() as conn:
        rows = conn.execute(
            """SELECT id, created_at, tickers, start_date, end_date,
                      expected_return, volatility, sharpe,
                      basket_return, nifty_return, max_weight, num_portfolios
               FROM portfolios WHERE user_id=? ORDER BY created_at DESC""",
            (user_id,),
        ).fetchall()
    if not rows:
        return pd.DataFrame()
    cols = ["id", "created_at", "tickers", "start_date", "end_date",
            "expected_return", "volatility", "sharpe",
            "basket_return", "nifty_return", "max_weight", "num_portfolios"]
    return pd.DataFrame(rows, columns=cols)


def get_portfolio_owner(portfolio_id: int) -> int | None:
    """Return the user_id for a portfolio, or None if legacy/missing."""
    with _connect() as conn:
        row = conn.execute("SELECT user_id FROM portfolios WHERE id=?", (portfolio_id,)).fetchone()
    return row[0] if row else None
