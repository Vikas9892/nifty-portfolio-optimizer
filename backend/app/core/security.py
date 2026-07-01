import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt

from backend.app.core.config import settings

# ── Password (bcrypt directly — avoids passlib/bcrypt 4.x compat issues) ─────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "email": email, "exp": expire, "type": "access"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: int) -> str:
    """Returns a raw opaque token (stored hashed in DB)."""
    token = secrets.token_urlsafe(48)
    return token


def decode_access_token(token: str) -> dict:
    """Returns payload dict. Raises JWTError if invalid/expired."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


# ── Refresh token helpers ────────────────────────────────────────────────────

def hash_token(raw: str) -> str:
    """SHA-256 hash of a refresh token for safe DB storage."""
    return hashlib.sha256(raw.encode()).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
