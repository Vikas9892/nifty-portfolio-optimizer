"""
Integration tests for /api/v1/portfolio — tests authorization, CRUD, and
cross-user access controls using the FastAPI TestClient.

External data calls (yfinance, optimizer) are mocked so these tests run
offline and deterministically.
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import numpy as np
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_prices(*tickers: str) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    idx = pd.date_range("2020-01-01", periods=252, freq="B")
    return pd.DataFrame(rng.lognormal(size=(252, len(tickers))), index=idx, columns=list(tickers))


OPTIMIZE_PAYLOAD = {
    "stocks": ["TCS.NS", "INFY.NS"],
    "start": "2020-01-01",
    "end": "2023-01-01",
    "max_weight": 0.40,
}

_MOCK_WEIGHTS = {"TCS.NS": 0.40, "INFY.NS": 0.60}


def _mock_optimize():
    p1 = patch("backend.app.services.portfolio_service.get_prices",
               return_value=_make_prices("TCS.NS", "INFY.NS"))
    p2 = patch("backend.app.services.portfolio_service.optimize_portfolio",
               return_value=(None, None, _MOCK_WEIGHTS, 0.18, 0.22, 0.82))
    p3 = patch("backend.app.services.portfolio_service.compare_with_nifty",
               return_value=(0.18, 0.12))
    return p1, p2, p3


@pytest.fixture()
def second_user(client):
    """Register a second user and return {access_token, refresh_token, user}."""
    resp = client.post("/api/v1/auth/register", json={
        "name": "Other User",
        "email": "other@example.com",
        "password": "Other1234",
    })
    assert resp.status_code == 201
    data = resp.json()["data"]
    return {
        "user": data["user"],
        "access_token": data["tokens"]["access_token"],
        "refresh_token": data["tokens"]["refresh_token"],
    }


# ── POST /portfolio/optimize ──────────────────────────────────────────────────

class TestOptimize:
    def test_201_returns_portfolio(self, client, auth_headers):
        p1, p2, p3 = _mock_optimize()
        with p1, p2, p3:
            resp = client.post("/api/v1/portfolio/optimize", json=OPTIMIZE_PAYLOAD,
                               headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert "portfolio_id" in data
        assert data["sharpe"] > 0
        assert abs(sum(data["weights"].values()) - 1.0) < 1e-6

    def test_401_without_token(self, client):
        p1, p2, p3 = _mock_optimize()
        with p1, p2, p3:
            resp = client.post("/api/v1/portfolio/optimize", json=OPTIMIZE_PAYLOAD)
        assert resp.status_code == 401

    def test_422_with_empty_stocks(self, client, auth_headers):
        resp = client.post("/api/v1/portfolio/optimize",
                           json={**OPTIMIZE_PAYLOAD, "stocks": []},
                           headers=auth_headers)
        assert resp.status_code == 422

    def test_422_with_bad_dates(self, client, auth_headers):
        resp = client.post("/api/v1/portfolio/optimize",
                           json={**OPTIMIZE_PAYLOAD, "start": "not-a-date"},
                           headers=auth_headers)
        assert resp.status_code == 422


# ── GET /portfolio/history ────────────────────────────────────────────────────

class TestHistory:
    def test_200_empty_history_for_new_user(self, client, auth_headers):
        resp = client.get("/api/v1/portfolio/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_401_without_token(self, client):
        resp = client.get("/api/v1/portfolio/history")
        assert resp.status_code == 401

    def test_history_contains_saved_portfolio(self, client, auth_headers):
        p1, p2, p3 = _mock_optimize()
        with p1, p2, p3:
            client.post("/api/v1/portfolio/optimize", json=OPTIMIZE_PAYLOAD,
                        headers=auth_headers)
        resp = client.get("/api/v1/portfolio/history", headers=auth_headers)
        assert len(resp.json()["data"]) == 1


# ── GET /portfolio/{id} ───────────────────────────────────────────────────────

class TestGetById:
    def test_200_owner_gets_detail(self, client, auth_headers):
        p1, p2, p3 = _mock_optimize()
        with p1, p2, p3:
            pid = client.post("/api/v1/portfolio/optimize", json=OPTIMIZE_PAYLOAD,
                              headers=auth_headers).json()["data"]["portfolio_id"]
        resp = client.get(f"/api/v1/portfolio/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        assert "weights" in resp.json()["data"]

    def test_403_other_user_cannot_access(self, client, auth_headers, second_user):
        p1, p2, p3 = _mock_optimize()
        with p1, p2, p3:
            pid = client.post("/api/v1/portfolio/optimize", json=OPTIMIZE_PAYLOAD,
                              headers=auth_headers).json()["data"]["portfolio_id"]
        other_headers = {"Authorization": f"Bearer {second_user['access_token']}"}
        resp = client.get(f"/api/v1/portfolio/{pid}", headers=other_headers)
        assert resp.status_code == 403

    def test_404_for_missing_portfolio(self, client, auth_headers):
        resp = client.get("/api/v1/portfolio/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_401_without_token(self, client):
        resp = client.get("/api/v1/portfolio/1")
        assert resp.status_code == 401


# ── DELETE /portfolio/{id} ────────────────────────────────────────────────────

class TestDelete:
    def test_200_owner_can_delete(self, client, auth_headers):
        p1, p2, p3 = _mock_optimize()
        with p1, p2, p3:
            pid = client.post("/api/v1/portfolio/optimize", json=OPTIMIZE_PAYLOAD,
                              headers=auth_headers).json()["data"]["portfolio_id"]
        resp = client.delete(f"/api/v1/portfolio/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        # Portfolio gone
        assert client.get(f"/api/v1/portfolio/{pid}", headers=auth_headers).status_code == 404

    def test_403_cross_user_delete(self, client, auth_headers, second_user):
        p1, p2, p3 = _mock_optimize()
        with p1, p2, p3:
            pid = client.post("/api/v1/portfolio/optimize", json=OPTIMIZE_PAYLOAD,
                              headers=auth_headers).json()["data"]["portfolio_id"]
        other_headers = {"Authorization": f"Bearer {second_user['access_token']}"}
        resp = client.delete(f"/api/v1/portfolio/{pid}", headers=other_headers)
        assert resp.status_code == 403

    def test_404_delete_nonexistent(self, client, auth_headers):
        resp = client.delete("/api/v1/portfolio/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_401_without_token(self, client):
        resp = client.delete("/api/v1/portfolio/1")
        assert resp.status_code == 401


# ── Full portfolio lifecycle flow ─────────────────────────────────────────────

class TestPortfolioLifecycle:
    def test_optimize_save_history_delete_history_empty(self, client, auth_headers):
        p1, p2, p3 = _mock_optimize()
        with p1, p2, p3:
            pid = client.post("/api/v1/portfolio/optimize", json=OPTIMIZE_PAYLOAD,
                              headers=auth_headers).json()["data"]["portfolio_id"]

        assert len(client.get("/api/v1/portfolio/history", headers=auth_headers).json()["data"]) == 1
        client.delete(f"/api/v1/portfolio/{pid}", headers=auth_headers)
        assert client.get("/api/v1/portfolio/history", headers=auth_headers).json()["data"] == []
