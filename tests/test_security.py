"""Unit tests for backend/app/core/security.py — pure functions, no I/O."""

import time

import pytest
from jose import JWTError

from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
    verify_password,
)


# ── Password hashing ──────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        h = hash_password("secret123")
        assert h != "secret123"

    def test_correct_password_verifies(self):
        h = hash_password("MyPass1")
        assert verify_password("MyPass1", h) is True

    def test_wrong_password_fails(self):
        h = hash_password("MyPass1")
        assert verify_password("different", h) is False

    def test_empty_password_hashes(self):
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("x", h) is False

    def test_two_hashes_differ(self):
        """bcrypt uses a random salt — same password → different hashes."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


# ── JWT access tokens ─────────────────────────────────────────────────────────

class TestJWT:
    def test_create_and_decode_round_trip(self):
        token = create_access_token(user_id=42, email="a@b.com")
        payload = decode_access_token(token)
        assert payload["sub"] == "42"
        assert payload["email"] == "a@b.com"
        assert payload["type"] == "access"

    def test_tampered_token_raises(self):
        token = create_access_token(1, "x@x.com")
        tampered = token[:-4] + "XXXX"
        with pytest.raises(JWTError):
            decode_access_token(tampered)

    def test_wrong_secret_raises(self, monkeypatch):
        from backend.app.core import security as sec
        token = create_access_token(1, "x@x.com")
        monkeypatch.setattr(sec.settings, "jwt_secret_key", "wrong-secret")
        with pytest.raises(JWTError):
            decode_access_token(token)

    def test_expired_token_raises(self, monkeypatch):
        """Force expiry by setting expire_minutes to 0 and sleeping 1 s."""
        from backend.app.core import security as sec
        monkeypatch.setattr(sec.settings, "access_token_expire_minutes", 0)
        token = create_access_token(1, "x@x.com")
        time.sleep(1)
        with pytest.raises(JWTError):
            decode_access_token(token)

    def test_token_type_field_is_access(self):
        token = create_access_token(99, "z@z.com")
        assert decode_access_token(token)["type"] == "access"


# ── Refresh token helpers ─────────────────────────────────────────────────────

class TestRefreshTokenHelpers:
    def test_create_refresh_token_is_opaque_string(self):
        token = create_refresh_token(user_id=1)
        assert isinstance(token, str)
        assert len(token) >= 32   # urlsafe_b64 of 48 bytes = 64 chars

    def test_two_refresh_tokens_are_unique(self):
        t1 = create_refresh_token(1)
        t2 = create_refresh_token(1)
        assert t1 != t2

    def test_hash_token_deterministic(self):
        raw = "some-raw-token"
        assert hash_token(raw) == hash_token(raw)

    def test_hash_token_different_inputs(self):
        assert hash_token("a") != hash_token("b")

    def test_hash_token_length(self):
        """SHA-256 hex digest is always 64 characters."""
        assert len(hash_token("anything")) == 64

    def test_refresh_token_expiry_in_future(self):
        from datetime import datetime, timezone
        exp = refresh_token_expiry()
        assert exp > datetime.now(timezone.utc)
