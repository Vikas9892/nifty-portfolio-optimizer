"""Unit tests for AuthService — uses a real temp DB, no HTTP layer."""

import pytest

from backend.app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from backend.app.services.auth_service import AuthService
from backend.app.utils.exceptions import AuthenticationError, ConflictError


@pytest.fixture()
def svc(tmp_db):
    return AuthService()


class TestRegister:
    def test_successful_register_returns_auth_response(self, svc):
        req = RegisterRequest(name="Alice", email="alice@test.com", password="Pass1234")
        resp = svc.register(req)
        assert resp.user.email == "alice@test.com"
        assert resp.user.name == "Alice"
        assert resp.tokens.access_token
        assert resp.tokens.refresh_token
        assert resp.tokens.token_type == "bearer"
        assert resp.tokens.expires_in == 900  # 15 min * 60

    def test_duplicate_email_raises_conflict(self, svc):
        req = RegisterRequest(name="Bob", email="bob@test.com", password="Pass1234")
        svc.register(req)
        with pytest.raises(ConflictError):
            svc.register(req)

    def test_audit_log_is_written(self, svc, tmp_db):
        import sqlite3
        svc.register(RegisterRequest(name="Ana", email="ana@t.com", password="Pass1234"))
        conn = sqlite3.connect(str(tmp_db))
        rows = conn.execute("SELECT action FROM audit_logs").fetchall()
        conn.close()
        actions = [r[0] for r in rows]
        assert "USER_REGISTERED" in actions


class TestLogin:
    def test_correct_credentials_return_tokens(self, svc):
        svc.register(RegisterRequest(name="Cal", email="cal@t.com", password="Pass1234"))
        resp = svc.login(LoginRequest(email="cal@t.com", password="Pass1234"))
        assert resp.user.email == "cal@t.com"
        assert resp.tokens.access_token

    def test_wrong_password_raises_authentication_error(self, svc):
        svc.register(RegisterRequest(name="Dan", email="dan@t.com", password="Pass1234"))
        with pytest.raises(AuthenticationError):
            svc.login(LoginRequest(email="dan@t.com", password="WRONG"))

    def test_unknown_email_raises_authentication_error(self, svc):
        with pytest.raises(AuthenticationError):
            svc.login(LoginRequest(email="nobody@x.com", password="pass"))

    def test_login_and_register_tokens_are_strings(self, svc):
        req = RegisterRequest(name="Eva", email="eva@t.com", password="Pass1234")
        reg_resp = svc.register(req)
        login_resp = svc.login(LoginRequest(email="eva@t.com", password="Pass1234"))
        assert isinstance(reg_resp.tokens.access_token, str)
        assert isinstance(login_resp.tokens.access_token, str)


class TestRefresh:
    def test_valid_refresh_returns_new_token_pair(self, svc):
        auth = svc.register(RegisterRequest(name="Fay", email="fay@t.com", password="Pass1234"))
        old_rt = auth.tokens.refresh_token
        new_tokens = svc.refresh(RefreshRequest(refresh_token=old_rt))
        assert new_tokens.access_token
        assert new_tokens.refresh_token
        assert new_tokens.refresh_token != old_rt

    def test_reusing_refresh_token_raises_authentication_error(self, svc):
        auth = svc.register(RegisterRequest(name="Gil", email="gil@t.com", password="Pass1234"))
        rt = auth.tokens.refresh_token
        svc.refresh(RefreshRequest(refresh_token=rt))
        with pytest.raises(AuthenticationError):
            svc.refresh(RefreshRequest(refresh_token=rt))

    def test_invalid_refresh_token_raises(self, svc):
        with pytest.raises(AuthenticationError):
            svc.refresh(RefreshRequest(refresh_token="totally-fake-token"))


class TestLogout:
    def test_logout_revokes_refresh_token(self, svc):
        auth = svc.register(RegisterRequest(name="Hal", email="hal@t.com", password="Pass1234"))
        rt = auth.tokens.refresh_token
        svc.logout(rt, auth.user.id)
        with pytest.raises(AuthenticationError):
            svc.refresh(RefreshRequest(refresh_token=rt))
