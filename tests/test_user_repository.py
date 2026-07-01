"""Unit tests for UserRepository — exercises the DB through the repository layer."""

import pytest

from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.auth import UserResponse
from backend.app.utils.exceptions import ConflictError, NotFoundError


@pytest.fixture()
def repo(tmp_db):
    return UserRepository()


class TestCreate:
    def test_returns_user_response(self, repo):
        user = repo.create("Alice", "alice@test.com", "hashed_pw")
        assert isinstance(user, UserResponse)
        assert user.email == "alice@test.com"
        assert user.name == "Alice"
        assert user.is_active is True
        assert user.id is not None

    def test_duplicate_email_raises_conflict(self, repo):
        repo.create("Alice", "alice@test.com", "hash")
        with pytest.raises(ConflictError) as exc_info:
            repo.create("Alice 2", "alice@test.com", "hash")
        assert "already registered" in str(exc_info.value.message)

    def test_different_emails_both_saved(self, repo):
        u1 = repo.create("A", "a@test.com", "h")
        u2 = repo.create("B", "b@test.com", "h")
        assert u1.id != u2.id


class TestGetById:
    def test_existing_user(self, repo):
        created = repo.create("Bob", "bob@test.com", "h")
        fetched = repo.get_by_id(created.id)
        assert fetched.email == "bob@test.com"

    def test_missing_user_raises_not_found(self, repo):
        with pytest.raises(NotFoundError):
            repo.get_by_id(99999)


class TestGetByEmailWithHash:
    def test_returns_dict_with_password_hash(self, repo):
        repo.create("Carol", "carol@test.com", "secret_hash")
        row = repo.get_by_email_with_hash("carol@test.com")
        assert row is not None
        assert row["password_hash"] == "secret_hash"

    def test_missing_email_returns_none(self, repo):
        assert repo.get_by_email_with_hash("nobody@x.com") is None
