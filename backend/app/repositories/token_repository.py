from datetime import datetime, timezone

from backend.app.models import database as db
from backend.app.utils.exceptions import AuthenticationError


class TokenRepository:
    def save(self, user_id: int, token_hash: str, expires_at: datetime) -> None:
        db.save_refresh_token(user_id, token_hash, expires_at)

    def validate(self, token_hash: str) -> dict:
        """Return token row or raise AuthenticationError."""
        row = db.get_refresh_token(token_hash)
        if not row:
            raise AuthenticationError("Refresh token is invalid.")
        if row["is_revoked"]:
            raise AuthenticationError("Refresh token has been revoked.")
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            raise AuthenticationError("Refresh token has expired.")
        return row

    def revoke(self, token_hash: str) -> None:
        db.revoke_refresh_token(token_hash)

    def revoke_all(self, user_id: int) -> None:
        db.revoke_all_user_tokens(user_id)
