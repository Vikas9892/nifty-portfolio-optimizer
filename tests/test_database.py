"""Unit tests for backend/app/models/database.py — DB layer with temp SQLite."""

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import backend.app.models.database as db


class TestTableInitialisation:
    def test_all_tables_created(self, tmp_db):
        conn = sqlite3.connect(str(tmp_db))
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        conn.close()
        assert {"users", "refresh_tokens", "audit_logs", "portfolios", "portfolio_weights", "prices"} <= tables

    def test_portfolios_has_user_id_column(self, tmp_db):
        conn = sqlite3.connect(str(tmp_db))
        cols = {r[1] for r in conn.execute("PRAGMA table_info(portfolios)").fetchall()}
        conn.close()
        assert "user_id" in cols

    def test_init_is_idempotent(self, tmp_db):
        """Calling init_all_tables() twice must not raise."""
        db.init_all_tables()
        db.init_all_tables()


class TestUserCRUD:
    def test_create_user_returns_dict(self, tmp_db):
        row = db.create_user("Alice", "a@a.com", "hashed")
        assert row["id"] is not None
        assert row["name"] == "Alice"
        assert row["email"] == "a@a.com"
        assert row["is_active"] == 1

    def test_get_user_by_id(self, tmp_db):
        row = db.create_user("Bob", "b@b.com", "hash2")
        fetched = db.get_user_by_id(row["id"])
        assert fetched is not None
        assert fetched["email"] == "b@b.com"

    def test_get_user_by_id_missing_returns_none(self, tmp_db):
        assert db.get_user_by_id(99999) is None

    def test_get_user_by_email(self, tmp_db):
        db.create_user("Carol", "c@c.com", "hash3")
        row = db.get_user_by_email("c@c.com")
        assert row is not None
        assert row["name"] == "Carol"
        assert "password_hash" in row

    def test_get_user_by_email_missing_returns_none(self, tmp_db):
        assert db.get_user_by_email("nobody@x.com") is None


class TestRefreshTokenCRUD:
    def test_save_and_fetch_token(self, tmp_db):
        user = db.create_user("D", "d@d.com", "h")
        exp = datetime.now(timezone.utc) + timedelta(days=7)
        db.save_refresh_token(user["id"], "tok_hash_abc", exp)
        row = db.get_refresh_token("tok_hash_abc")
        assert row is not None
        assert row["user_id"] == user["id"]
        assert row["is_revoked"] == 0

    def test_fetch_missing_token_returns_none(self, tmp_db):
        assert db.get_refresh_token("nonexistent") is None

    def test_revoke_token(self, tmp_db):
        user = db.create_user("E", "e@e.com", "h")
        exp = datetime.now(timezone.utc) + timedelta(days=7)
        db.save_refresh_token(user["id"], "rev_hash", exp)
        db.revoke_refresh_token("rev_hash")
        row = db.get_refresh_token("rev_hash")
        assert row["is_revoked"] == 1

    def test_revoke_all_user_tokens(self, tmp_db):
        user = db.create_user("F", "f@f.com", "h")
        exp = datetime.now(timezone.utc) + timedelta(days=7)
        db.save_refresh_token(user["id"], "h1", exp)
        db.save_refresh_token(user["id"], "h2", exp)
        db.revoke_all_user_tokens(user["id"])
        assert db.get_refresh_token("h1")["is_revoked"] == 1
        assert db.get_refresh_token("h2")["is_revoked"] == 1


class TestAuditLog:
    def test_log_audit_inserts(self, tmp_db):
        user = db.create_user("G", "g@g.com", "h")
        db.log_audit(user["id"], "LOGIN_SUCCESS", "ip=127.0.0.1")
        conn = sqlite3.connect(str(tmp_db))
        rows = conn.execute("SELECT * FROM audit_logs WHERE user_id=?", (user["id"],)).fetchall()
        conn.close()
        assert len(rows) == 1
        assert "LOGIN_SUCCESS" in rows[0]

    def test_audit_log_without_user(self, tmp_db):
        """Anonymous audit entries (e.g. failed login) must not raise."""
        db.log_audit(None, "LOGIN_FAILED", "email=anon@x.com")


class TestPortfolioOwnership:
    def test_save_portfolio_for_user_stamps_user_id(self, tmp_db):
        user = db.create_user("H", "h@h.com", "h")
        pid = db.save_portfolio_for_user(
            user_id=user["id"],
            tickers=["TCS.NS", "INFY.NS"],
            start_date="2020-01-01", end_date="2023-01-01",
            expected_return=0.15, volatility=0.20, sharpe=0.75,
            basket_return=0.14, nifty_return=0.10,
            max_weight=0.30, num_portfolios=0,
            weights={"TCS.NS": 0.5, "INFY.NS": 0.5},
        )
        assert db.get_portfolio_owner(pid) == user["id"]

    def test_get_portfolio_owner_missing_returns_none(self, tmp_db):
        assert db.get_portfolio_owner(99999) is None
