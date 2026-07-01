"""
Unit tests for PortfolioService.

External calls (yfinance, scipy optimiser, benchmark) are mocked so tests
run fast and offline.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from backend.app.schemas.auth import UserResponse
from backend.app.schemas.portfolio import OptimizeRequest
from backend.app.services.portfolio_service import PortfolioService
from backend.app.utils.exceptions import AuthorizationError, NotFoundError, OptimizationError, ValidationError


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(user_id: int = 1) -> UserResponse:
    return UserResponse(
        id=user_id, name="Alice", email="alice@test.com",
        created_at="2024-01-01T00:00:00+00:00", is_active=True,
    )


def _price_df(*tickers: str) -> pd.DataFrame:
    """Minimal 2-stock price DataFrame the service accepts."""
    import numpy as np
    rng = np.random.default_rng(42)
    idx = pd.date_range("2020-01-01", periods=252, freq="B")
    return pd.DataFrame(
        rng.lognormal(size=(252, len(tickers))),
        index=idx, columns=list(tickers),
    )


@pytest.fixture()
def svc(tmp_db):
    return PortfolioService()


# ── optimize() ────────────────────────────────────────────────────────────────

class TestOptimize:
    def _patch_externals(self, price_df=None, weights=None):
        """Return context-manager stack mocking all three external calls."""
        if price_df is None:
            price_df = _price_df("TCS.NS", "INFY.NS")
        if weights is None:
            weights = {"TCS.NS": 0.40, "INFY.NS": 0.60}
        p_prices = patch("backend.app.services.portfolio_service.get_prices", return_value=price_df)
        p_opt    = patch("backend.app.services.portfolio_service.optimize_portfolio",
                         return_value=(None, None, weights, 0.18, 0.22, 0.82))
        p_bench  = patch("backend.app.services.portfolio_service.compare_with_nifty",
                         return_value=(0.18, 0.12))
        return p_prices, p_opt, p_bench

    def test_weights_sum_to_one(self, svc):
        p1, p2, p3 = self._patch_externals()
        with p1, p2, p3:
            req = OptimizeRequest(stocks=["TCS.NS", "INFY.NS"],
                                  start="2020-01-01", end="2023-01-01", max_weight=0.40)
            resp = svc.optimize(req, _make_user())
        total = sum(resp.weights.values())
        assert abs(total - 1.0) < 1e-6

    def test_sharpe_exists_and_positive(self, svc):
        p1, p2, p3 = self._patch_externals()
        with p1, p2, p3:
            req = OptimizeRequest(stocks=["TCS.NS", "INFY.NS"],
                                  start="2020-01-01", end="2023-01-01", max_weight=0.40)
            resp = svc.optimize(req, _make_user())
        assert resp.sharpe > 0

    def test_volatility_positive(self, svc):
        p1, p2, p3 = self._patch_externals()
        with p1, p2, p3:
            req = OptimizeRequest(stocks=["TCS.NS", "INFY.NS"],
                                  start="2020-01-01", end="2023-01-01", max_weight=0.40)
            resp = svc.optimize(req, _make_user())
        assert resp.volatility > 0

    def test_portfolio_id_returned(self, svc):
        p1, p2, p3 = self._patch_externals()
        with p1, p2, p3:
            req = OptimizeRequest(stocks=["TCS.NS", "INFY.NS"],
                                  start="2020-01-01", end="2023-01-01", max_weight=0.40)
            resp = svc.optimize(req, _make_user())
        assert isinstance(resp.portfolio_id, int)
        assert resp.portfolio_id > 0

    def test_alpha_computed(self, svc):
        p1, p2, p3 = self._patch_externals()
        with p1, p2, p3:
            req = OptimizeRequest(stocks=["TCS.NS", "INFY.NS"],
                                  start="2020-01-01", end="2023-01-01", max_weight=0.40)
            resp = svc.optimize(req, _make_user())
        assert pytest.approx(resp.alpha, abs=1e-6) == resp.basket_return - resp.nifty_return

    def test_empty_data_raises_validation_error(self, svc):
        # Schema needs >=2 stocks; we pass valid tickers but mock get_prices to return empty
        with patch("backend.app.services.portfolio_service.get_prices", return_value=pd.DataFrame()):
            with pytest.raises(ValidationError, match="No price data"):
                svc.optimize(
                    OptimizeRequest(stocks=["BAD.NS", "X.NS"], start="2020-01-01", end="2023-01-01"),
                    _make_user(),
                )

    def test_single_column_df_raises_validation_error(self, svc):
        """get_prices returned only 1 column (only 1 ticker had data) — must raise."""
        df = _price_df("TCS.NS")   # single-column DataFrame
        with patch("backend.app.services.portfolio_service.get_prices", return_value=df):
            with pytest.raises(ValidationError, match="at least 2"):
                svc.optimize(
                    OptimizeRequest(stocks=["TCS.NS", "X.NS"], start="2020-01-01", end="2023-01-01"),
                    _make_user(),
                )

    def test_optimiser_exception_raises_optimization_error(self, svc):
        df = _price_df("TCS.NS", "INFY.NS")
        with patch("backend.app.services.portfolio_service.get_prices", return_value=df), \
             patch("backend.app.services.portfolio_service.optimize_portfolio",
                   side_effect=RuntimeError("solver failed")):
            with pytest.raises(OptimizationError):
                svc.optimize(
                    OptimizeRequest(stocks=["TCS.NS", "INFY.NS"],
                                    start="2020-01-01", end="2023-01-01"),
                    _make_user(),
                )

    def test_max_weight_respected_in_request(self, svc):
        """Verify OptimizeRequest carries max_weight through to the service."""
        captured: list[float] = []
        df = _price_df("A.NS", "B.NS")

        def _fake_opt(data, max_weight):
            captured.append(max_weight)
            return None, None, {"A.NS": max_weight, "B.NS": 1 - max_weight}, 0.1, 0.2, 0.5

        with patch("backend.app.services.portfolio_service.get_prices", return_value=df), \
             patch("backend.app.services.portfolio_service.optimize_portfolio", side_effect=_fake_opt), \
             patch("backend.app.services.portfolio_service.compare_with_nifty", return_value=(0.1, 0.08)):
            svc.optimize(OptimizeRequest(stocks=["A.NS", "B.NS"],
                                         start="2020-01-01", end="2023-01-01", max_weight=0.45),
                         _make_user())
        assert captured[0] == 0.45


# ── get_history() ─────────────────────────────────────────────────────────────

class TestGetHistory:
    def test_empty_initially(self, svc):
        assert svc.get_history(_make_user()) == []

    def test_returns_saved_portfolio(self, svc):
        p1, p2, p3 = TestOptimize()._patch_externals()
        with p1, p2, p3:
            svc.optimize(
                OptimizeRequest(stocks=["TCS.NS", "INFY.NS"],
                                start="2020-01-01", end="2023-01-01"),
                _make_user(),
            )
        history = svc.get_history(_make_user())
        assert len(history) == 1


# ── delete() ─────────────────────────────────────────────────────────────────

class TestDelete:
    def test_delete_own_portfolio(self, svc):
        p1, p2, p3 = TestOptimize()._patch_externals()
        with p1, p2, p3:
            resp = svc.optimize(
                OptimizeRequest(stocks=["TCS.NS", "INFY.NS"],
                                start="2020-01-01", end="2023-01-01"),
                _make_user(),
            )
        del_resp = svc.delete(resp.portfolio_id, _make_user())
        assert del_resp.portfolio_id == resp.portfolio_id
        assert svc.get_history(_make_user()) == []

    def test_delete_missing_raises_not_found(self, svc):
        with pytest.raises(NotFoundError):
            svc.delete(99999, _make_user())

    def test_delete_cross_user_raises_authorization_error(self, svc):
        p1, p2, p3 = TestOptimize()._patch_externals()
        with p1, p2, p3:
            resp = svc.optimize(
                OptimizeRequest(stocks=["TCS.NS", "INFY.NS"],
                                start="2020-01-01", end="2023-01-01"),
                _make_user(user_id=1),
            )
        with pytest.raises(AuthorizationError):
            svc.delete(resp.portfolio_id, _make_user(user_id=2))
