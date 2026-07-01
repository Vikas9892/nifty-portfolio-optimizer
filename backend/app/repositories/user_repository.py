from backend.app.models import database as db
from backend.app.schemas.auth import UserResponse
from backend.app.utils.exceptions import ConflictError, NotFoundError


class UserRepository:
    def create(self, name: str, email: str, password_hash: str) -> UserResponse:
        if db.get_user_by_email(email):
            raise ConflictError(f"Email '{email}' is already registered.")
        row = db.create_user(name, email, password_hash)
        return self._to_schema(row)

    def get_by_id(self, user_id: int) -> UserResponse:
        row = db.get_user_by_id(user_id)
        if not row:
            raise NotFoundError("User")
        return self._to_schema(row)

    def get_by_email_with_hash(self, email: str) -> dict | None:
        """Return raw row (including password_hash). None if not found."""
        return db.get_user_by_email(email)

    @staticmethod
    def _to_schema(row: dict) -> UserResponse:
        return UserResponse(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            created_at=row["created_at"],
            is_active=bool(row["is_active"]),
        )
