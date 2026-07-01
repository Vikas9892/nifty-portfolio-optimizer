# System Design Evolution — Nifty Portfolio Optimizer

> Version: 4.0.0 · Last updated: 2026-07-02

This document traces the architecture from the first prototype to the current production-grade distributed system. Each phase explains what changed, what pain point drove the change, and what was left behind.

---

## Timeline at a Glance

```
v1 (Phase 1)  ── Single-file script, hardcoded tickers, CLI output
     │
v2 (Phase 2)  ── FastAPI REST API, SQLite, Pydantic schemas
     │
v3 (Phase 3)  ── React frontend, JWT authentication, bcrypt
     │
v4 (Phase 4)  ── Repository pattern, service layer, SQLAlchemy Core
     │
v5 (Phase 5)  ── JWT refresh tokens, Axios interceptor, protected routes
     │
v6 (Phase 6)  ── Test suite, CI/CD, coverage gates, ruff + black linting
     │
v7 (Phase 7)  ── Docker Compose, PostgreSQL, Redis, Nginx, async workers
     │
v8 (Phase 8)  ── RQ worker pool, APScheduler, cache-aside, circuit breaker
     │
v9 (Phase 9)  ── Feature flags, distributed lock, DLQ, alerting, JSON logs
     │
v10 (current) ── System design docs, benchmarks, production checklists
```

---

## Phase 1 — The Prototype (v1)

### What existed

```python
# app.py  (~80 lines, everything in one file)
import yfinance as yf
from pypfopt import EfficientFrontier, expected_returns, risk_models

TICKERS = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
START, END = "2022-01-01", "2023-01-01"

prices = yf.download(TICKERS, start=START, end=END)["Close"]
mu = expected_returns.mean_historical_return(prices)
sigma = risk_models.sample_cov(prices)
ef = EfficientFrontier(mu, sigma)
weights = ef.max_sharpe()
print(weights)
```

### What worked
- Zero setup — one file, one command, results printed.
- Correct math — PyPfOpt's EfficientFrontier gives proper mean-variance optimization.

### What broke at scale
- Tickers hardcoded. Every change required editing source code.
- No persistence — results vanished after the process exited.
- No API — usable only via terminal by the developer.
- Yahoo Finance calls happened synchronously; if it took 30s, the user waited 30s.

### Decision: keep the PyPfOpt core, build everything else around it.

---

## Phase 2 — REST API (v2)

### What changed

```
app.py (single file)
    ↓
backend/
├── main.py           # FastAPI app, CORS, /health
├── routers/
│   ├── portfolio.py  # POST /optimize
│   └── health.py
└── services/
    └── optimizer.py  # wraps PyPfOpt logic
```

### Why FastAPI over Flask

| | Flask | FastAPI |
|---|---|---|
| Type validation | Manual | Pydantic v2 built-in |
| Async support | Requires async extensions | Native ASGI |
| OpenAPI docs | 3rd-party extension | Built-in /docs |
| Performance | WSGI (synchronous) | ASGI (async by default) |

FastAPI's automatic request validation meant we could stop writing `if not request.json.get("tickers"): return error(400)` boilerplate.

### What remained painful
- SQLite was added for persistence, but all SQL was inline in route handlers.
- No auth — anyone who knew the URL could optimize portfolios and read saved results.
- All work happened in the request cycle — optimization blocked the Uvicorn event loop.

---

## Phase 3 — Authentication + Frontend (v3)

### What changed

```
+ frontend/           # React 18 + TypeScript + Vite
  ├── src/
  │   ├── pages/     # Login, Register, Dashboard
  │   ├── api/       # Axios clients
  │   └── types/     # TypeScript interfaces
+ backend/app/
  ├── routers/auth.py    # /register, /login
  └── services/auth.py   # bcrypt + JWT
```

### Auth design decisions

**bcrypt rounds=12** — At the time of writing, rounds=12 takes ~265ms per hash on commodity hardware. This is intentional: it means an attacker brute-forcing a stolen hash database can test only ~3-4 passwords per second per CPU core.

**JWT (stateless) over sessions** — Sessions require server-side storage (Redis or DB). JWTs embed user identity in the token itself, making horizontal scaling trivial: any replica can verify any token without shared session storage.

**Access + Refresh token pair** — Short-lived access tokens (30 min) limit the blast radius of a stolen token. Refresh tokens (7 days) avoid forcing users to re-login daily.

### What remained painful
- All SQL still inline in services — no clear separation of data access.
- One repo for everything — no modular structure, imports becoming circular.
- No test suite — refactoring was risky.

---

## Phase 4 — Service Layer + Repository Pattern (v4)

### What changed

```
backend/app/
├── repositories/          # NEW — all SQL lives here
│   ├── user_repository.py
│   ├── portfolio_repository.py
│   └── job_repository.py
├── services/              # now purely business logic
│   ├── auth_service.py
│   ├── portfolio_service.py
│   └── market_service.py
└── dependencies.py        # FastAPI Depends() wiring
```

### Why the repository pattern at this stage

The pain point: `auth_service.py` had both bcrypt logic and `SELECT * FROM users WHERE email=?` inline. When we needed to add a "last login" timestamp, we had to grep through service files to find all SQL touching the users table.

The repository pattern gave us:
- One file per table — `user_repository.py` owns all user-related SQL.
- Services that read like English: `user = self._repo.get_by_email(email)`.
- The ability to mock `UserRepository` in unit tests without mocking SQLAlchemy.

### What remained painful
- No async job queue — optimization still blocked requests (5–30s wait).
- No caching — every request hit Yahoo Finance, rate limits became a real problem.
- No test coverage requirement — tests existed but weren't enforced.

---

## Phase 5 — Token Refresh + Auth Polish (v5)

### What changed

```
+ backend/app/routers/auth.py   POST /auth/refresh endpoint
+ frontend/src/api/axiosClient.ts  Interceptor: auto-refresh on 401
+ frontend/src/context/AuthContext.tsx  Token rotation in state
```

### The interceptor pattern

Before Phase 5, a 401 response from the API would just show an error. Users had to manually log out and log back in when their 30-minute access token expired.

The Axios interceptor pattern solves this transparently:
1. Response interceptor catches 401.
2. Calls `POST /auth/refresh` with the stored refresh token.
3. Gets new token pair, updates localStorage.
4. Retries the original request with the new token.
5. User never sees a login page unless their refresh token also expired.

**Token rotation**: On each refresh, a new refresh token is also issued. This means a stolen refresh token becomes invalid after one use.

---

## Phase 6 — Testing + CI/CD (v6)

### What changed

```
+ tests/
│   ├── test_auth.py         # 35 tests
│   ├── test_portfolio.py    # 41 tests
│   ├── test_market.py       # 18 tests
│   └── conftest.py          # shared fixtures
+ .github/workflows/ci.yml   # lint → test → build → deploy
+ pyproject.toml             # ruff, black, coverage config
```

### Coverage threshold = 80%

We set `fail_under = 80` rather than 100% for deliberate reasons:
- Worker tasks (`backend/app/workers/`) are integration-tested via E2E smoke tests, not unit tests. Mocking RQ internals would test the mock, not the code.
- APScheduler (`scheduler.py`) is tested in staging with a real Redis, not in CI.
- The 80% gate catches regressions without forcing mock-heavy tests of infrastructure glue.

### What the CI pipeline does

```
push to main
    │
    ├─ ruff check (linting)
    ├─ black --check (formatting)
    │
    ├─ pytest --cov (Python 3.11)
    │   └── fail if coverage < 80%
    │
    ├─ pytest --cov (Python 3.12)  # compatibility check
    │
    └─ docker compose up --build  # smoke test all services
       └── /health returns 200 within 30s
```

---

## Phase 7 — Docker + PostgreSQL + Redis + Nginx (v7)

### What changed

```
+ docker-compose.yml     # 6 services: api, frontend, nginx, postgres, redis, worker
+ nginx/nginx.conf       # reverse proxy + static file serving
+ Dockerfile (backend)   # multi-stage: builder + slim runtime image
+ Dockerfile (frontend)  # build → Nginx serve
+ .env.example           # all config documented
```

### Service topology

```
nginx:443 → frontend:3000 (static)
nginx:443 → api:8000 (proxy /api/*)
api:8000  → postgres:5432
api:8000  → redis:6379
worker    → redis:6379 (job queue)
worker    → postgres:5432
```

### Why PostgreSQL over SQLite for production

SQLite uses file-level locking. Under concurrent writes (multiple workers updating job status simultaneously), the DB lock becomes a bottleneck. PostgreSQL uses row-level locking and connection pooling, handling 100+ concurrent writes without contention.

SQLite is still used in development because it requires zero setup — just a file path.

---

## Phase 8 — Scalability (v8)

### What changed

```
+ backend/app/workers/         # RQ task queue
│   └── tasks.py               # portfolio_optimize_task, market_refresh_task
+ backend/app/services/
│   ├── scheduler.py           # APScheduler: market refresh every 15 min
│   ├── cache_service.py       # Redis cache-aside
│   └── job_service.py         # full job lifecycle
+ backend/app/utils/retry.py   # CircuitBreaker + exponential backoff
```

### The async job pattern

Before Phase 8, the optimize endpoint ran PyPfOpt synchronously:

```
Client → POST /optimize → [wait 5-30s for Yahoo + PyPfOpt] → 200 {weights}
```

Under load (50 concurrent users), 50 Uvicorn workers would all be blocked in Python code. FastAPI's event loop can't yield to other requests during CPU-bound work.

After Phase 8:

```
Client → POST /optimize → 202 {job_id}    [< 50ms]
                             ↓
Client → GET /jobs/{id}  [2s poll interval]
                             ↓
Worker → fetches job → runs PyPfOpt → marks complete
```

The API stays responsive regardless of optimization load. Workers scale independently.

### Circuit breaker for Yahoo Finance

Yahoo Finance is a free, unofficial API with no SLA. It fails:
- When rate-limited (>2000 requests/day from one IP).
- On market open/close times (data not yet available).
- On Yahoo maintenance windows.

Without a circuit breaker, 50 queued jobs all wait 30s for timeout, tying up workers. With the circuit breaker:
- After 5 failures, the circuit opens.
- Subsequent calls fail in ~0.1ms (no network I/O).
- After 60s, the circuit half-opens for a single probe.

---

## Phase 9 — SRE / Reliability (v9)

### What changed

```
+ backend/app/services/
│   ├── feature_flags.py      # Redis-backed runtime toggles
│   ├── distributed_lock.py   # Redis SET NX EX + Lua release
│   └── dlq_service.py        # Dead letter queue (7-day TTL)
+ backend/app/routers/sre.py  # /api/v1/sre/* admin endpoints
+ backend/app/utils/logger.py # JSON structured logging (_JSONFormatter)
+ alertmanager/
│   ├── alerting_rules.yml    # 6 Prometheus alert rules
│   └── alertmanager.yml      # Email / Slack / PagerDuty routing
+ docs/
    ├── reliability.md
    ├── chaos_testing.md
    ├── capacity_planning.md
    ├── disaster_recovery.md
    ├── cost_estimate.md
    └── security_audit.md
```

### Why feature flags at this stage

After deploying to production, we hit the classic problem: how do you disable a feature that's misbehaving without a deployment?

Feature flags solve this:
- `ENABLE_CACHE = false` → bypass Redis cache if it's causing stale data.
- `ENABLE_WORKERS = false` → run optimization synchronously if RQ workers are down.
- `ENABLE_SCHEDULER = false` → stop market refresh if Yahoo is rate-limiting.

Changes take effect within seconds via the `/sre/feature-flags/{flag}` endpoint. No deployment, no restart.

### Why a distributed lock for the scheduler

In production with 3 API replicas, each has its own APScheduler instance. Without a lock, all 3 fire at minute :00, making 150 Yahoo API calls for 50 symbols instead of 50.

Redis `SET NX EX` is the canonical distributed lock primitive:
- `SET lock_name value NX EX ttl` — atomic: set only if not exists, with expiry.
- Lua compare-and-delete on release: only the lock holder can release (prevents accidental release by another process whose clock skewed).

### Why a dead letter queue

Without a DLQ, jobs that fail 3 times disappear silently. Support gets "where's my optimization?" and there's no paper trail.

With the DLQ:
- Snapshots of failed jobs stored for 7 days in Redis.
- `/sre/dlq` shows the failure reason, retry count, and timestamp.
- One-click retry after fixing the underlying issue.

---

## What Was Left Behind (Technical Debt Acknowledged)

| Item | Why left | Resolution path |
|---|---|---|
| SQLAlchemy async | Using `databases` library (async), not `asyncpg` directly | Migrate to SQLAlchemy 2.0 async core |
| Token blocklist | Refresh tokens can't be revoked server-side | Add Redis-backed token blocklist |
| Multi-tenancy | One DB, one schema per user (by user_id FK) | Add organization model if B2B |
| PDF export | Feature flag exists (`ENABLE_PDF_REPORTS`) but not implemented | Add WeasyPrint/ReportLab |
| WebSocket progress | Jobs polled every 2s (minor over-fetch) | Replace with WebSocket push |
| Rate limiting | No per-user API rate limits | Add `slowapi` middleware |

---

## Evolution Summary Table

| Version | Key Addition | Trigger |
|---|---|---|
| v1 | Script, PyPfOpt core | Prove the math works |
| v2 | FastAPI REST, SQLite | Make it callable via HTTP |
| v3 | React SPA, JWT auth | Multi-user, persistent UI |
| v4 | Repository + Service layers | SQL in service files was unmaintainable |
| v5 | Token refresh, Axios interceptor | Users complained about being logged out |
| v6 | Tests, CI/CD, linting | "Works on my machine" deployment failures |
| v7 | Docker, PostgreSQL, Redis, Nginx | Production readiness |
| v8 | Worker queue, scheduler, circuit breaker | API too slow under load |
| v9 | Feature flags, DLQ, distributed lock, alerting | Operational visibility after first prod incident |
| v10 | Docs, benchmarks, production checklist | Onboarding new engineers + interview readiness |
