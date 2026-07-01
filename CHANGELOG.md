# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [2.1.0] — 2026-07-01 — Phase 6: Software Engineering Excellence

### Added
- **Unit tests** — 109 backend tests covering security, auth service, portfolio service, repositories, and database layer (89% coverage)
- **Integration tests** — Full HTTP flows for auth and portfolio endpoints via FastAPI TestClient
- **Frontend tests** — 26 Vitest + React Testing Library tests for Button, MetricCard, ProtectedRoute, and AuthContext
- **GitHub Actions CI** — Multi-job pipeline: backend tests (Python 3.11/3.12), frontend tests, TypeScript check, build verification, and health check
- **Ruff linting** — Zero linting errors across `backend/app/`
- **Black + isort** — Consistent formatting and import ordering
- **Pre-commit hooks** — Auto-run ruff, black, isort on every commit
- **Dependabot** — Automatic dependency update PRs for Python and npm
- **`/health`** — Liveness probe endpoint (returns 200 if process is alive)
- **`/ready`** — Readiness probe endpoint (checks DB connectivity)
- **`/version`** — Build version and runtime environment
- **`docs/`** — architecture, testing, security, API, and deployment guides
- **`CONTRIBUTING.md`** — Developer onboarding guide
- **`CODE_OF_CONDUCT.md`** — Community standards
- **`LICENSE`** — MIT license
- **GitHub issue and PR templates**
- **`pyproject.toml`** — Unified configuration for pytest, coverage, ruff, black, isort, mypy

### Fixed
- `B904`: All `raise` inside `except` blocks now use `raise ... from exc`
- `B905`: All `zip()` calls now use `strict=True`
- `UP017`: Replaced `datetime.timezone.utc` with `datetime.UTC` (Python 3.11+)
- `I001`: Fixed import ordering across all backend modules

---

## [2.0.0] — 2026-07-01 — Phase 5: Production Backend + Auth Frontend

### Added
- JWT authentication: access tokens (15 min) + refresh tokens (7 days) with single-use rotation
- `POST /api/v1/auth/register` — bcrypt password hashing, email validation
- `POST /api/v1/auth/login` — returns access + refresh token pair
- `GET /api/v1/auth/me` — returns current authenticated user
- `POST /api/v1/auth/refresh` — rotates refresh token
- `POST /api/v1/auth/logout` — revokes refresh token
- Global exception handler with `AppException` hierarchy
- `SuccessResponse[T]` / `ErrorResponse` envelope on all responses
- Request/response logging middleware with ms timing (`X-Process-Time-Ms` header)
- Rate limiting via `slowapi` (per-endpoint limits)
- API versioning (`/api/v1/`)
- Repository pattern: Service → Repository → SQLite
- Audit logs table
- React login and register pages with dark/light theme support
- JWT stored in localStorage with Axios interceptors
- 401 auto-refresh with queue (prevents race conditions)
- `AuthContext` with silent `/me` verification on mount
- `ProtectedRoute` component with `from` location state
- pydantic-settings BaseSettings reading `.env`

### Fixed
- Replaced `passlib[bcrypt]` with direct `bcrypt` (incompatible with bcrypt 4.x on Python 3.13)
- SQLite transaction isolation bug in `create_user` (now builds dict from insertion values directly)
- `BenchmarkRequest` `NameError` in model_validator (added `from __future__ import annotations`)
- Portfolio ownership check now correctly rejects orphan portfolios (`owner != user_id`)

---

## [1.0.0] — Phase 1–4: Core Optimizer

### Added
- Markowitz mean-variance optimizer with Ledoit-Wolf covariance shrinkage
- Full Nifty 50 universe (50 stocks)
- SQLite price cache (yfinance source)
- Sharpe ratio maximization (scipy)
- Nifty 50 benchmark comparison
- Streamlit dashboard (later replaced with React)
- React + Vite frontend with Recharts visualizations
- Dark/light theme
- Portfolio history (save, view, delete)
