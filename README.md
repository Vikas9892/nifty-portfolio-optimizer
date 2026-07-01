# Nifty Portfolio Optimizer

> Mean-variance portfolio optimization for the **Nifty 50** universe — production-grade, full-stack, deployed.

[![CI](https://github.com/Vikas9892/nifty-portfolio-optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/Vikas9892/nifty-portfolio-optimizer/actions/workflows/ci.yml)
[![CD](https://github.com/Vikas9892/nifty-portfolio-optimizer/actions/workflows/deploy.yml/badge.svg)](https://github.com/Vikas9892/nifty-portfolio-optimizer/actions/workflows/deploy.yml)
[![Coverage](https://img.shields.io/badge/coverage-81.7%25-brightgreen)](docs/benchmarks.md)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](backend/Dockerfile)
[![Node](https://img.shields.io/badge/node-20-blue)](frontend/package.json)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## Live Demo

| Service | URL |
|---|---|
| **Frontend** | https://nifty-portfolio-optimizer.vercel.app |
| **Backend API** | https://nifty-api.up.railway.app |
| **Swagger / OpenAPI** | https://nifty-api.up.railway.app/docs |
| **ReDoc** | https://nifty-api.up.railway.app/redoc |

> **Demo video** (5 min walkthrough): *[▶ Watch on YouTube](https://youtu.be/placeholder)* — login, optimize a Nifty 50 basket, explore the efficient frontier, inspect Prometheus metrics, and tour the SRE admin panel (circuit breakers, feature flags, DLQ).

---

## Screenshots

| Login | Optimize | Dashboard |
|---|---|---|
| ![Login](docs/screenshots/login.png) | ![Optimize](docs/screenshots/optimize.png) | ![Dashboard](docs/screenshots/dashboard.png) |

| Efficient Frontier | History | SRE Admin |
|---|---|---|
| ![Frontier](docs/screenshots/frontier.png) | ![History](docs/screenshots/history.png) | ![SRE](docs/screenshots/sre.png) |

> To add screenshots: run `docker compose up`, open `http://localhost:3000`, capture each page, and save to `docs/screenshots/`.

---

## What It Does

Given a user-selected basket of Nifty 50 stocks and a date range, the optimizer:

1. Fetches OHLCV history from Yahoo Finance (Redis-cached, 24h TTL)
2. Estimates expected returns and the covariance matrix
3. Solves the **max-Sharpe** mean-variance optimization via PyPortfolioOpt + CVXPY
4. Returns portfolio weights, Sharpe ratio, expected return, and volatility
5. Overlays the result on a Monte Carlo efficient frontier (10k simulations)
6. Benchmarks realized performance against the Nifty 50 index

All optimization runs are **async** (Redis queue → RQ worker) so the API responds in < 50ms regardless of portfolio size.

---

## Architecture

```
 Browser / Mobile
      │ HTTPS
      ▼
  Nginx (TLS, static serving)
      │ /api/*
      ▼
 FastAPI (ASGI · Uvicorn · Python 3.11)
   Auth ─ Portfolio ─ Market ─ Jobs ─ SRE
      │               │              │
  bcrypt          Services      Redis
  JWT HS256    + Repositories  ├── Cache (24h TTL)
  refresh tok   SQLAlchemy     ├── Job Queue (RQ)
                Core            ├── Feature Flags
      │               │         ├── Distributed Lock
      ▼               ▼         └── Dead Letter Queue
 PostgreSQL      RQ Workers
   (prod)      ┌──────────────┐
 SQLite (dev)  │ PyPfOpt      │──→ Yahoo Finance
               │ EfficientFr. │    (Circuit Breaker)
               │ max_sharpe() │
               └──────────────┘
                       │
              APScheduler (market refresh · 15 min)
                       │
              Prometheus + Grafana + Alertmanager
```

Full diagrams, sequence flows, and LLD: **[docs/system_design.md](docs/system_design.md)**

---

## Tech Stack

**Backend**

| | |
|---|---|
| Framework | FastAPI 0.111 + Uvicorn (ASGI) |
| Language | Python 3.11 |
| Database | PostgreSQL 16 (prod) · SQLite (dev) |
| ORM | SQLAlchemy Core (no ORM, raw expressions) |
| Queue | Redis + RQ (async job processing) |
| Cache | Redis cache-aside, 24h TTL |
| Auth | JWT HS256 (python-jose) + bcrypt |
| Optimizer | PyPortfolioOpt + CVXPY + NumPy |
| Data | yfinance (Yahoo Finance) |
| Observability | Prometheus · Grafana · Alertmanager |
| Scheduler | APScheduler + Redis distributed lock |
| Resilience | Circuit breaker · Feature flags · DLQ |

**Frontend**

| | |
|---|---|
| Framework | React 18 + TypeScript |
| Build | Vite 5 |
| Styling | Tailwind CSS |
| Charts | Recharts |
| Icons | Lucide React |
| HTTP | Axios (with JWT refresh interceptor) |
| Testing | Vitest + Testing Library |

**Infrastructure**

| | |
|---|---|
| Container | Docker + Docker Compose |
| Proxy | Nginx |
| CI | GitHub Actions (lint → test → build → deploy) |
| Backend deploy | Railway |
| Frontend deploy | Vercel |
| Images | GitHub Container Registry (GHCR) |

---

## Quick Start (Docker)

```bash
git clone https://github.com/Vikas9892/nifty-portfolio-optimizer.git
cd nifty-portfolio-optimizer
cp .env.example .env        # review defaults — works out of the box for local dev
docker compose up --build
```

Open **http://localhost:3000** — register an account and optimize your first portfolio.

| Service | Local URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin/admin) |
| Alertmanager | http://localhost:9093 |

---

## Folder Structure

```
nifty-portfolio-optimizer/
├── backend/
│   ├── app/
│   │   ├── core/           # Settings, DI, security helpers
│   │   ├── middleware/     # Correlation ID, request logging
│   │   ├── models/         # SQLAlchemy table definitions
│   │   ├── repositories/   # All SQL (UserRepo, PortfolioRepo, JobRepo)
│   │   ├── routers/        # HTTP route handlers (thin — no logic)
│   │   ├── schemas/        # Pydantic request / response DTOs
│   │   ├── services/       # Business logic (Auth, Portfolio, Cache, DLQ…)
│   │   ├── utils/          # Logger, retry + circuit breaker
│   │   └── workers/        # RQ background task functions
│   ├── Dockerfile
│   └── main.py             # App factory, middleware, router wiring
├── frontend/
│   ├── src/
│   │   ├── components/     # UI components (charts, layout, auth)
│   │   ├── context/        # AuthContext, PortfolioContext
│   │   ├── hooks/          # useAuth, useOptimize, useJobPoller
│   │   ├── pages/          # Login, Dashboard, Optimize, History, Admin
│   │   └── services/       # Axios API clients
│   └── Dockerfile
├── docs/
│   ├── system_design.md        # Architecture + 8 sequence diagrams
│   ├── low_level_design.md     # 12 design patterns with WHY
│   ├── design_decisions.md     # 11 ADRs (FastAPI, Redis, JWT…)
│   ├── benchmarks.md           # Real latency numbers
│   ├── evolution.md            # v1 script → v10 distributed system
│   ├── production_checklist.md # 50-point deploy gate
│   └── decisions/              # Individual ADR files
├── tests/                  # pytest (163 tests, 81.7% coverage)
├── scripts/
│   ├── benchmark.py        # Latency benchmarks (run: python scripts/benchmark.py)
│   ├── chaos_test.sh       # Smoke + fault injection tests
│   └── entrypoint.sh       # Docker entrypoint (waits for DB)
├── alertmanager/           # Prometheus alert rules + routing
├── grafana/                # Dashboard JSON provisioning
├── nginx/                  # nginx.conf
├── docker-compose.yml      # Full local stack (9 services)
├── docker-compose.prod.yml # Production overrides
├── railway.toml            # Railway backend deployment config
├── render.yaml             # Render alternative config
└── vercel.json             # Vercel frontend deployment config
```

---

## API Reference

Full interactive docs at `/docs` (Swagger) or `/redoc`.

**Authentication**

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create account |
| `POST` | `/api/v1/auth/login` | Get access + refresh tokens |
| `POST` | `/api/v1/auth/refresh` | Rotate tokens |
| `GET` | `/api/v1/auth/me` | Current user profile |

**Portfolio**

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/portfolio/optimize` | Enqueue optimization job → 202 `{job_id}` |
| `GET` | `/api/v1/portfolio/` | List saved portfolios |
| `POST` | `/api/v1/portfolio/save` | Save a completed optimization |
| `DELETE` | `/api/v1/portfolio/{id}` | Delete a portfolio |

**Jobs**

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/jobs/{id}` | Poll job status: `pending → running → completed` |

**SRE / Admin**

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/sre/circuit-breakers` | All breaker states |
| `GET/PUT` | `/api/v1/sre/feature-flags/{flag}` | Read / toggle feature flag |
| `GET` | `/api/v1/sre/dlq` | Dead letter queue contents |
| `POST` | `/api/v1/sre/dlq/{id}/retry` | Re-queue a failed job |

**Observability**

| Path | Description |
|---|---|
| `GET /health` | Liveness probe |
| `GET /ready` | Readiness probe (checks DB + Redis) |
| `GET /metrics` | Prometheus metrics |

---

## Testing

```bash
# Run all tests with coverage
python -m pytest --cov=backend/app --cov-fail-under=80 -q

# Run specific test file
python -m pytest tests/test_auth.py -v

# Frontend tests
cd frontend && npm run test:coverage
```

| | |
|---|---|
| Backend tests | 163 passing |
| Backend coverage | 81.7% |
| Python versions | 3.11, 3.12 (matrix CI) |
| Frontend tests | Vitest + Testing Library |

---

## Deploy to Production

The GitHub Actions CD pipeline (`deploy.yml`) auto-deploys on every push to `main`. You need three things:

### 1. Backend → Railway

```bash
npm install -g @railway/cli
railway login                        # opens browser
railway init                         # link to your Railway project
railway add --plugin postgresql      # add Postgres
railway add --plugin redis           # add Redis
railway variables set JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
railway variables set ENVIRONMENT=production
railway up                           # first deploy
```

Copy the Railway public URL (e.g. `https://nifty-api.up.railway.app`).

### 2. Frontend → Vercel

```bash
npm install -g vercel
cd frontend
vercel                               # follow prompts, link GitHub repo
vercel env add VITE_API_URL          # paste your Railway backend URL
vercel --prod
```

Copy the Vercel URL (e.g. `https://nifty-portfolio-optimizer.vercel.app`).

### 3. Wire up CORS + CI secrets

```bash
# Tell the backend which frontend URL to allow:
railway variables set CORS_ORIGINS='["https://your-app.vercel.app"]'

# Add to GitHub repo secrets (Settings → Secrets → Actions):
# RAILWAY_TOKEN    — railway whoami --token
# VERCEL_TOKEN     — vercel whoami --token
# VERCEL_ORG_ID    — from .vercel/project.json after `vercel`
# VERCEL_PROJECT_ID — from .vercel/project.json after `vercel`
# BACKEND_URL      — your Railway URL (for smoke tests)
```

After this, every `git push main` triggers: lint → test → Docker build → Railway deploy → Vercel deploy → smoke test.

---

## Documentation

| Doc | What's inside |
|---|---|
| [System Design](docs/system_design.md) | HLD, request flows, 8 sequence diagrams |
| [Low-Level Design](docs/low_level_design.md) | 12 patterns (Repository, Strategy, Circuit Breaker…) |
| [Design Decisions](docs/design_decisions.md) | 11 ADRs with Problem / Alternatives / Tradeoffs |
| [Benchmarks](docs/benchmarks.md) | Real latency: 0.022ms JWT, 20ms optimizer, 265ms bcrypt |
| [Evolution](docs/evolution.md) | v1 script → v10 distributed system |
| [Production Checklist](docs/production_checklist.md) | 50-point deploy gate |
| [API Reference](docs/api.md) | Request/response schemas |
| [Reliability](docs/reliability.md) | SLOs, DLQ runbook, circuit breaker policy |
| [Load Testing](docs/load_testing.md) | Locust results at 10–1000 concurrent users |
| [Capacity Planning](docs/capacity_planning.md) | Resource projections |
| [Disaster Recovery](docs/disaster_recovery.md) | RTO/RPO, restore runbook |
| [Security Audit](docs/security_audit.md) | OWASP checklist, threat model |

---

## Mathematical Foundation

**Objective**: maximize the Sharpe ratio

```
maximize   (w′μ − r_f) / √(w′Σw)

subject to  Σwᵢ = 1
            0 ≤ wᵢ ≤ w_max  ∀i
```

- `w` — weight vector (decision variable)
- `μ` — annualized expected returns (`mean_daily × 252`)
- `Σ` — sample covariance matrix (`× 252`)
- `r_f` — risk-free rate (default 5%)
- `w_max` — position cap (default 30%)

PyPortfolioOpt transforms this quasi-convex problem into an equivalent convex QP solved via CVXPY. A 10,000-portfolio Monte Carlo simulation validates the result against the feasible set.

**Stock universe**: Full Nifty 50 across 14 sectors (IT, Banking, Financial Services, Energy, FMCG, Pharma, Auto, Metals, Cement, Infra, Telecom, Consumer, Healthcare, Agro).

---

## License

MIT — see [LICENSE](LICENSE).
