"""
Integration tests for /api/v1/auth — full HTTP flow through FastAPI TestClient
against an isolated in-memory SQLite database.

The fixtures (client, registered_user, auth_headers) live in tests/conftest.py.
"""

import pytest


# ── POST /register ────────────────────────────────────────────────────────────

class TestRegister:
    def test_201_on_valid_payload(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "name": "Alice", "email": "alice@test.com", "password": "Pass1234",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["user"]["email"] == "alice@test.com"
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    def test_409_on_duplicate_email(self, client):
        payload = {"name": "Al", "email": "dup@test.com", "password": "Pass1234"}
        client.post("/api/v1/auth/register", json=payload)
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409
        assert resp.json()["success"] is False

    def test_422_on_missing_fields(self, client):
        resp = client.post("/api/v1/auth/register", json={"name": "Alice"})  # no email/password
        assert resp.status_code == 422

    def test_422_on_weak_password(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "name": "Al", "email": "a@test.com", "password": "weak",
        })
        assert resp.status_code == 422

    def test_422_on_invalid_email(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "name": "Al", "email": "not-an-email", "password": "Pass1234",
        })
        assert resp.status_code == 422


# ── POST /login ───────────────────────────────────────────────────────────────

class TestLogin:
    def test_200_on_correct_credentials(self, client, registered_user):
        resp = client.post("/api/v1/auth/login", json={
            "email": "test@example.com", "password": "Test1234",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["tokens"]["access_token"]

    def test_401_on_wrong_password(self, client, registered_user):
        resp = client.post("/api/v1/auth/login", json={
            "email": "test@example.com", "password": "WRONG",
        })
        assert resp.status_code == 401

    def test_401_on_unknown_email(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "nobody@x.com", "password": "Pass1234",
        })
        assert resp.status_code == 401


# ── GET /me ───────────────────────────────────────────────────────────────────

class TestMe:
    def test_200_with_valid_token(self, client, registered_user, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["email"] == "test@example.com"

    def test_401_with_no_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_401_with_bad_token(self, client):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
        assert resp.status_code == 401


# ── POST /refresh ─────────────────────────────────────────────────────────────

class TestRefresh:
    def test_200_returns_new_token_pair(self, client, registered_user):
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": registered_user["refresh_token"],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["access_token"]
        assert data["refresh_token"] != registered_user["refresh_token"]

    def test_401_on_reused_refresh_token(self, client, registered_user):
        rt = registered_user["refresh_token"]
        client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        assert resp.status_code == 401

    def test_401_on_invalid_refresh_token(self, client):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "fake-token"})
        assert resp.status_code == 401


# ── POST /logout ──────────────────────────────────────────────────────────────

class TestLogout:
    def test_200_on_valid_logout(self, client, registered_user, auth_headers):
        resp = client.post("/api/v1/auth/logout", headers=auth_headers, json={
            "refresh_token": registered_user["refresh_token"],
        })
        assert resp.status_code == 200

    def test_refresh_fails_after_logout(self, client, registered_user, auth_headers):
        rt = registered_user["refresh_token"]
        client.post("/api/v1/auth/logout", headers=auth_headers, json={"refresh_token": rt})
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        assert resp.status_code == 401


# ── Full authentication flow ──────────────────────────────────────────────────

class TestFullAuthFlow:
    def test_register_login_me_logout_no_refresh(self, client):
        # 1. Register
        r1 = client.post("/api/v1/auth/register", json={
            "name": "Flow User", "email": "flow@test.com", "password": "Pass1234",
        })
        assert r1.status_code == 201
        tokens = r1.json()["data"]["tokens"]

        # 2. /me works
        r2 = client.get("/api/v1/auth/me",
                         headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert r2.status_code == 200

        # 3. Logout
        r3 = client.post("/api/v1/auth/logout",
                          headers={"Authorization": f"Bearer {tokens['access_token']}"},
                          json={"refresh_token": tokens["refresh_token"]})
        assert r3.status_code == 200

        # 4. Refresh after logout must fail
        r4 = client.post("/api/v1/auth/refresh",
                          json={"refresh_token": tokens["refresh_token"]})
        assert r4.status_code == 401
