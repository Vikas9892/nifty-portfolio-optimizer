"""Unit tests for PortfolioRepository — tests DB CRUD and auth guards."""

import pytest

from backend.app.repositories.portfolio_repository import PortfolioRepository
from backend.app.schemas.portfolio import PortfolioDetail, PortfolioListItem
from backend.app.utils.exceptions import AuthorizationError, NotFoundError
import backend.app.models.database as db


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_user(name: str, email: str) -> dict:
    return db.create_user(name, email, "hash")


def _save_portfolio(repo: PortfolioRepository, user_id: int) -> int:
    return repo.save(
        user_id=user_id,
        tickers=["TCS.NS", "INFY.NS"],
        start_date="2020-01-01", end_date="2023-01-01",
        expected_return=0.15, volatility=0.20, sharpe=0.75,
        basket_return=0.14, nifty_return=0.10,
        max_weight=0.30, num_portfolios=0,
        weights={"TCS.NS": 0.5, "INFY.NS": 0.5},
    )


@pytest.fixture()
def repo(tmp_db):
    return PortfolioRepository()


@pytest.fixture()
def user(tmp_db):
    return _make_user("Alice", "alice@test.com")


@pytest.fixture()
def other_user(tmp_db):
    return _make_user("Bob", "bob@test.com")


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestSave:
    def test_returns_positive_integer_id(self, repo, user):
        pid = _save_portfolio(repo, user["id"])
        assert isinstance(pid, int)
        assert pid > 0

    def test_saves_user_id(self, repo, user):
        pid = _save_portfolio(repo, user["id"])
        owner = db.get_portfolio_owner(pid)
        assert owner == user["id"]


class TestGetAllForUser:
    def test_empty_for_new_user(self, repo, user):
        assert repo.get_all_for_user(user["id"]) == []

    def test_returns_own_portfolios(self, repo, user):
        _save_portfolio(repo, user["id"])
        _save_portfolio(repo, user["id"])
        items = repo.get_all_for_user(user["id"])
        assert len(items) == 2
        assert all(isinstance(i, PortfolioListItem) for i in items)

    def test_does_not_return_other_users_portfolios(self, repo, user, other_user):
        _save_portfolio(repo, other_user["id"])
        assert repo.get_all_for_user(user["id"]) == []


class TestGetById:
    def test_owner_can_get_own_portfolio(self, repo, user):
        pid = _save_portfolio(repo, user["id"])
        detail = repo.get_by_id(pid, user["id"])
        assert isinstance(detail, PortfolioDetail)
        assert detail.id == pid

    def test_weights_returned(self, repo, user):
        pid = _save_portfolio(repo, user["id"])
        detail = repo.get_by_id(pid, user["id"])
        assert "TCS.NS" in detail.weights
        assert "INFY.NS" in detail.weights

    def test_missing_portfolio_raises_not_found(self, repo, user):
        with pytest.raises(NotFoundError):
            repo.get_by_id(99999, user["id"])

    def test_wrong_user_raises_authorization_error(self, repo, user, other_user):
        pid = _save_portfolio(repo, user["id"])
        with pytest.raises(AuthorizationError):
            repo.get_by_id(pid, other_user["id"])


class TestDelete:
    def test_owner_can_delete(self, repo, user):
        pid = _save_portfolio(repo, user["id"])
        resp = repo.delete(pid, user["id"])
        assert resp.portfolio_id == pid
        with pytest.raises(NotFoundError):
            repo.get_by_id(pid, user["id"])

    def test_delete_missing_raises_not_found(self, repo, user):
        with pytest.raises(NotFoundError):
            repo.delete(99999, user["id"])

    def test_wrong_user_cannot_delete(self, repo, user, other_user):
        pid = _save_portfolio(repo, user["id"])
        with pytest.raises(AuthorizationError):
            repo.delete(pid, other_user["id"])
        # Original should still exist
        assert repo.get_by_id(pid, user["id"]).id == pid
