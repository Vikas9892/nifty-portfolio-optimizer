from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from backend.app.models import database as db
from backend.app.core.security import decode_access_token
from backend.app.schemas.auth import UserResponse
from backend.app.utils.exceptions import AuthenticationError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    """FastAPI dependency — validates JWT and returns the authenticated user."""
    try:
        payload = decode_access_token(token)
        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type.")
        user_id: int = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise AuthenticationError("Token is invalid or has expired.")

    row = db.get_user_by_id(user_id)
    if not row:
        raise AuthenticationError("User no longer exists.")
    if not row["is_active"]:
        raise AuthenticationError("Account is deactivated.")

    return UserResponse(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        created_at=row["created_at"],
        is_active=bool(row["is_active"]),
    )
