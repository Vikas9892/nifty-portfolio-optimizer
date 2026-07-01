from backend.app.core.config import settings
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
    verify_password,
)
from backend.app.repositories.audit_repository import AuditRepository
from backend.app.repositories.token_repository import TokenRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from backend.app.utils.exceptions import AuthenticationError
from backend.app.utils.logger import logger


class AuthService:
    def __init__(self) -> None:
        self._users = UserRepository()
        self._tokens = TokenRepository()
        self._audit = AuditRepository()

    def register(self, req: RegisterRequest, ip: str | None = None) -> AuthResponse:
        hashed = hash_password(req.password)
        user = self._users.create(name=req.name, email=req.email, password_hash=hashed)
        logger.info("USER_REGISTERED | email=%s", req.email)
        self._audit.log(user.id, "USER_REGISTERED", f"email={req.email}", ip)
        return self._issue_tokens(user, ip)

    def login(self, req: LoginRequest, ip: str | None = None) -> AuthResponse:
        row = self._users.get_by_email_with_hash(req.email)
        if not row or not verify_password(req.password, row["password_hash"]):
            self._audit.log(None, "LOGIN_FAILED", f"email={req.email}", ip)
            raise AuthenticationError("Invalid email or password.")
        if not row["is_active"]:
            raise AuthenticationError("Account is deactivated.")
        user = UserResponse(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            created_at=row["created_at"],
            is_active=bool(row["is_active"]),
        )
        logger.info("LOGIN_SUCCESS | user_id=%s", user.id)
        self._audit.log(user.id, "LOGIN_SUCCESS", ip=ip)
        return self._issue_tokens(user, ip)

    def refresh(self, req: RefreshRequest) -> TokenResponse:
        token_hash = hash_token(req.refresh_token)
        row = self._tokens.validate(token_hash)  # raises if invalid
        self._tokens.revoke(token_hash)  # rotate: one-time use
        from backend.app.models import database as db

        user_row = db.get_user_by_id(row["user_id"])
        if not user_row or not user_row["is_active"]:
            raise AuthenticationError("User account is not accessible.")
        user = UserResponse(
            id=user_row["id"],
            name=user_row["name"],
            email=user_row["email"],
            created_at=user_row["created_at"],
            is_active=bool(user_row["is_active"]),
        )
        logger.info("TOKEN_REFRESHED | user_id=%s", user.id)
        return self._build_token_response(user)

    def logout(self, refresh_token: str, user_id: int) -> None:
        token_hash = hash_token(refresh_token)
        self._tokens.revoke(token_hash)
        self._audit.log(user_id, "LOGOUT")
        logger.info("LOGOUT | user_id=%s", user_id)

    def logout_all(self, user_id: int) -> None:
        """Revoke every session for this user (e.g. on password change)."""
        self._tokens.revoke_all(user_id)
        self._audit.log(user_id, "LOGOUT_ALL_SESSIONS")
        logger.info("LOGOUT_ALL | user_id=%s", user_id)

    # ── Private helpers ──────────────────────────────────────────────────────

    def _issue_tokens(self, user: UserResponse, ip: str | None) -> AuthResponse:
        tokens = self._build_token_response(user)
        token_hash = hash_token(tokens.refresh_token)
        self._tokens.save(user.id, token_hash, refresh_token_expiry())
        return AuthResponse(user=user, tokens=tokens)

    def _build_token_response(self, user: UserResponse) -> TokenResponse:
        access = create_access_token(user.id, user.email)
        refresh = create_refresh_token(user.id)
        expire_secs = settings.access_token_expire_minutes * 60
        return TokenResponse(access_token=access, refresh_token=refresh, expires_in=expire_secs)
