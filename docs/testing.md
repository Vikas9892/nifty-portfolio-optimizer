# Testing Guide

## Backend Tests

### Run all tests
```bash
python -m pytest tests/ -v
```

### Run with coverage (must reach 80%)
```bash
python -m pytest tests/ --cov=backend/app --cov-report=term-missing
```

### Run only unit tests
```bash
python -m pytest tests/ -k "not integration" -v
```

### Run only integration tests
```bash
python -m pytest tests/integration/ -v
```

### Run a specific test file
```bash
python -m pytest tests/test_security.py -v
```

## Frontend Tests

### Run all tests
```bash
cd frontend && npm test
```

### Run with coverage
```bash
cd frontend && npm run test:coverage
```

### Watch mode (during development)
```bash
cd frontend && npm run test:watch
```

## Test Structure

```
tests/
├── conftest.py                     # Shared fixtures: tmp_db, client, auth_headers
├── test_security.py                # Pure functions (bcrypt, JWT) — no I/O
├── test_auth_service.py            # AuthService unit tests
├── test_portfolio_service.py       # PortfolioService (external calls mocked)
├── test_portfolio_repository.py    # Repository CRUD + auth guards
├── test_user_repository.py         # UserRepository CRUD
├── test_database.py                # DB layer — table init, CRUD, migration
└── integration/
    ├── test_auth_routes.py         # Full HTTP auth flow
    └── test_portfolio_routes.py    # Full HTTP portfolio flow + authorization

frontend/src/__tests__/
├── components/
│   ├── Button.test.tsx             # Variants, loading, click handlers
│   ├── MetricCard.test.tsx         # Label, value, delta, color
│   └── ProtectedRoute.test.tsx     # Redirect/render by auth state
└── context/
    └── AuthContext.test.tsx        # Login, register, logout, persistence
```

## Database Isolation

Every test that needs a database receives a fresh temporary SQLite file via the `tmp_db` fixture in `conftest.py`. This works by monkeypatching `src.database._connect` to return connections pointing at a pytest `tmp_path` file instead of `data/portfolio.db`.

```python
# conftest.py — how isolation works
@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    def _test_connect():
        return sqlite3.connect(str(db_file))
    monkeypatch.setattr(src.database, "_connect", _test_connect)
    backend.app.models.database.init_all_tables()
    return db_file
```

## Mocking External Services

Portfolio optimization calls yfinance and scipy. In tests, these are mocked:

```python
from unittest.mock import patch

with patch("backend.app.services.portfolio_service.get_prices", return_value=price_df), \
     patch("backend.app.services.portfolio_service.optimize_portfolio",
           return_value=(None, None, weights, ret, vol, sharpe)), \
     patch("backend.app.services.portfolio_service.compare_with_nifty",
           return_value=(basket_return, nifty_return)):
    resp = svc.optimize(req, user)
```

## Coverage Targets

| Layer | Current | Target |
|---|---|---|
| `backend/app` | 89% | ≥ 80% |
| `frontend/src` | — | ≥ 70% lines |
