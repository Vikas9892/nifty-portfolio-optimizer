# Design Decisions — Nifty Portfolio Optimizer

> Version: 4.0.0 · Last updated: 2026-07-02

Each decision is structured as: **Problem → Alternatives Considered → Decision → Tradeoffs**.

This is an expanded Architecture Decision Record (ADR) set, building on individual ADRs in `docs/decisions/`.

---

## DD-01 · FastAPI as the Backend Framework

**Problem**

We need a Python HTTP framework to serve a REST API. The optimization math is CPU-bound (PyPfOpt + NumPy), but data fetch (Yahoo Finance, DB queries) is I/O-bound. The framework needs to handle both well, with automatic request validation to prevent bad inputs reaching the optimizer.

**Alternatives Considered**

| Framework | Async | Auto-validation | OpenAPI | Performance |
|---|---|---|---|---|
| Flask | ❌ (WSGI) | ❌ manual | ❌ extension | ~2000 req/s |
| Django REST | ❌ (WSGI) | Partial | ❌ extension | ~1500 req/s |
| Tornado | ✅ | ❌ manual | ❌ | ~3000 req/s |
| **FastAPI** | **✅ ASGI** | **✅ Pydantic** | **✅ built-in** | **~4500 req/s** |

**Decision: FastAPI**

**Tradeoffs**

| Pro | Con |
|---|---|
| Pydantic v2 validation at zero marginal cost | Younger ecosystem than Flask/Django |
| Auto-generates `/docs` (Swagger) and `/redoc` | `Depends()` mental model unfamiliar to Flask devs |
| True async — I/O-bound work yields the event loop | CPU-bound work still needs workers (not async) |
| Type hints throughout = IDE autocompletion in routes | Slightly higher learning curve |

**Outcome**: 202 Accepted responses under 50ms. Validation errors return structured 422 with field-level detail. Zero manual `request.json.get()` calls.

---

## DD-02 · SQLAlchemy Core (not ORM)

**Problem**

We need database access that works with both SQLite (dev) and PostgreSQL (prod), without locking into a single dialect. We want SQL control without writing raw string queries everywhere.

**Alternatives Considered**

1. **Raw SQL strings** — Maximum control, terrible refactoring story. Column renames require grep.
2. **SQLAlchemy ORM** — Automatic relationships and lazy loading. Risk of N+1 queries. Magic that hides performance problems.
3. **SQLAlchemy Core** — SQL expression language: type-safe, composable, no magic loading.
4. **Tortoise ORM / SQLModel** — Async-first. Smaller ecosystem, fewer production battle-scars.

**Decision: SQLAlchemy Core with `databases` library for async**

```python
query = (
    portfolios.select()
    .where(portfolios.c.user_id == user_id)
    .order_by(portfolios.c.created_at.desc())
    .limit(20)
)
rows = await db.fetch_all(query)
```

**Tradeoffs**

| Pro | Con |
|---|---|
| Explicit SQL — no hidden N+1 queries | More verbose than ORM for simple CRUD |
| Same code works on SQLite and PostgreSQL | No auto-migration (Alembic still needed) |
| Core expressions are composable and refactorable | Relationships must be joined manually |
| Column-level type safety | Less "batteries included" than Django ORM |

---

## DD-03 · Redis for Cache, Queue, Feature Flags, and DLQ

**Problem**

We need four distinct capabilities:
1. **Cache** — Store market data (24h TTL) to avoid hammering Yahoo Finance.
2. **Job queue** — Async background processing of portfolio optimization.
3. **Feature flags** — Runtime toggles without deployments.
4. **Dead letter queue** — Persistent failed job storage.

**Alternatives Considered**

| Need | Alternative | Why Redis won |
|---|---|---|
| Cache | Memcached | No native data structures; no persistence |
| Cache | In-process dict | Doesn't survive restart; not shared across replicas |
| Queue | Celery + RabbitMQ | RabbitMQ adds another service; Celery config is complex |
| Queue | Redis + RQ | RQ is simpler; Redis is already there |
| Feature flags | LaunchDarkly | $200/month; overkill for 5 flags |
| Feature flags | DB table | DB write per flag check would be expensive |
| DLQ | SQS | AWS only; adds cloud vendor lock-in |

**Decision: Redis for all four**

**Tradeoffs**

| Pro | Con |
|---|---|
| One service handles four use cases | Single point of failure (mitigated by Redis AOF) |
| Sub-millisecond latency for flag checks | Memory-only by default (persistence requires config) |
| RQ workers need no additional infrastructure | Redis memory needs monitoring for DLQ growth |
| TTL-based expiry for both cache and DLQ entries | Not durable by default (vs. Postgres) |

**Graceful degradation**: All Redis operations are wrapped with `try/except`. Without Redis, the system runs in degraded mode: cache misses every time (falls through to Yahoo), feature flags use env-var defaults.

---

## DD-04 · JWT (Stateless Auth) over Sessions

**Problem**

We need authentication that works across multiple API replicas without shared state. A user authenticated to replica A should also be authenticated to replica B.

**Alternatives Considered**

1. **Server-side sessions + Redis** — Session ID in cookie, session data in Redis. Requires Redis for auth (coupling). Can be revoked.
2. **Database sessions** — Session row per user. Requires DB lookup per request (slower). Can be revoked.
3. **JWT (stateless)** — Token embeds claims, verified with shared secret. No storage required. Cannot be revoked without blocklist.
4. **OAuth2 + third-party IdP** — Outsource auth. Adds external dependency and complexity for a self-hosted app.

**Decision: JWT with access + refresh pair**

```
Access token:  HS256, 30 minutes, { sub: user_id, type: "access" }
Refresh token: HS256, 7 days,     { sub: user_id, type: "refresh" }
```

**Tradeoffs**

| Pro | Con |
|---|---|
| Stateless — scales horizontally trivially | Cannot revoke individual tokens without a blocklist |
| Any replica verifies any token (shared secret) | Secret key rotation invalidates all sessions |
| 30-min window limits stolen token blast radius | If refresh token is stolen, 7-day window |
| Rotation on refresh prevents refresh token reuse | Longer tokens = more bytes per request |

**Mitigations for cons**:
- Token rotation on every refresh: stolen refresh token invalidated after first legitimate use.
- Short access token TTL: stolen tokens expire in 30 min.
- HTTPS enforced in production: tokens not exposed in transit.

---

## DD-05 · Repository Pattern

**Problem**

SQL queries were scattered across service files. When we added a `last_login_at` column to users, we had to search every file. Tests that wanted to verify a query had to mock SQLAlchemy itself.

**Decision: Repository pattern** — See `docs/low_level_design.md#1-repository-pattern` for full detail.

**Key tradeoff**: More files, more indirection. Worthwhile because the alternative (SQL everywhere) scaled poorly past ~3 developers.

---

## DD-06 · Background Jobs with RQ (not Celery)

**Problem**

Portfolio optimization takes 5–30s (depending on ticker count and date range). Blocking the Uvicorn event loop for 30s per request means a single slow request blocks all other requests on that worker.

**Alternatives Considered**

| Option | Pros | Cons |
|---|---|---|
| `asyncio.run_in_executor` | No extra infrastructure | CPU-bound still blocks GIL; in-process |
| Celery | Mature, feature-rich | Complex config (brokers, backends, serializers) |
| **RQ (Redis Queue)** | Simple, Redis already present, easy to debug | Fewer advanced features than Celery |
| Dramatiq | Clean API, priorities | Less community; another dependency |
| AWS Lambda (async) | Infinitely scalable | Vendor lock-in; cold starts; no self-hosting |

**Decision: RQ**

```python
from rq import Queue
q = Queue(connection=redis_conn)
q.enqueue(portfolio_optimize_task, job_id)
```

**Tradeoffs**

| Pro | Con |
|---|---|
| Redis already in stack — no new service | No built-in priorities (configurable with multiple queues) |
| Dead simple API — `q.enqueue(fn, arg)` | No visual dashboard (use rq-dashboard separately) |
| Worker process is a plain Python script | Job state management requires custom `job_service.py` |
| Easy to debug: `rq info` shows queue depth | No Celery-style task chains or chords |

---

## DD-07 · React (not Next.js or Vue)

**Problem**

We need a frontend for a single-page application with:
- Authentication flow (login, register, token management).
- Portfolio dashboard with charts.
- Real-time job status polling.

**Alternatives Considered**

| Framework | SSR | Bundle size | Auth complexity | DX |
|---|---|---|---|---|
| Next.js | ✅ | Medium | Server-side auth possible | Complex for SPA |
| Vue 3 | ❌ | Small | Similar to React | Different ecosystem |
| Svelte | ❌ | Tiny | Less ecosystem | Fewer libraries |
| **React 18 + Vite** | ❌ (SPA) | Medium | Context API | Excellent |
| Angular | ❌ | Large | Built-in | Opinionated |

**Decision: React 18 + Vite + TypeScript**

**Tradeoffs**

| Pro | Con |
|---|---|
| Largest ecosystem (Recharts, React Query) | No SSR (SEO not a concern for a dashboard) |
| Context API sufficient for this app's state | More boilerplate than Svelte |
| TypeScript catches API contract mismatches | Build complexity vs. Vite (mitigated by Vite) |
| Vite HMR is fast in development | React's re-render model needs understanding |

**Why not Next.js**: Portfolio optimizer is a private dashboard, not a public website. SSR adds complexity (server component boundaries, hydration) with no benefit when there's nothing to SEO-index.

---

## DD-08 · Docker Compose for Development and Production

**Problem**

"Works on my machine" failures were common. The development setup required: Python 3.11, Node 18, SQLite (dev) or PostgreSQL (prod), Redis — all pinned to specific versions. New contributors needed 2 hours of setup.

**Alternatives Considered**

1. **Bare metal install instructions** — Documentation that rots; inconsistent versions.
2. **Vagrant** — Full VMs, slow to start, large disk.
3. **Docker Compose** — Containers with pinned versions, one command to start everything.
4. **Kubernetes (Minikube)** — Production-like, but massive complexity overhead for a dev env.

**Decision: Docker Compose**

```yaml
services:
  api:     { build: backend, ports: [8000] }
  frontend: { build: frontend, ports: [3000] }
  postgres: { image: postgres:16-alpine }
  redis:   { image: redis:7-alpine }
  worker:  { build: backend, command: rq worker }
  nginx:   { image: nginx:alpine }
  prometheus: { image: prom/prometheus }
  grafana:    { image: grafana/grafana }
  alertmanager: { image: prom/alertmanager }
```

**Tradeoffs**

| Pro | Con |
|---|---|
| One command (`docker compose up`) starts everything | Docker Desktop required on Windows/Mac |
| Pinned image versions in `docker-compose.yml` | Container overhead vs. bare metal (small for dev) |
| Same compose file used in production (with overrides) | Not the same as Kubernetes in production |
| Easy to scale workers: `docker compose up --scale worker=3` | No pod autoscaling (use Kubernetes for that) |

---

## DD-09 · PostgreSQL (not MySQL or MongoDB)

**Problem**

SQLite file-locking blocks concurrent writes. In production with 3 API replicas + 3 workers, 6 processes write simultaneously. We need a production-grade RDBMS.

**Alternatives Considered**

| DB | ACID | JSON support | Scalability | Reason rejected |
|---|---|---|---|---|
| MySQL | ✅ | ✅ (JSON type) | Good | Weaker JSON operators; PostgreSQL dialect is richer |
| MongoDB | ❌ (pre-4.0) | Native | Excellent | No joins; portfolio stock weights are relational |
| DynamoDB | ✅ (conditional) | Native | Excellent | AWS lock-in; complex queries |
| **PostgreSQL** | ✅ | ✅ (jsonb) | Excellent | Richest SQL dialect + jsonb for weights |

**Decision: PostgreSQL 16**

**Tradeoffs**

| Pro | Con |
|---|---|
| Row-level locking eliminates concurrency bottleneck | More setup than SQLite |
| `jsonb` column for weights (no schema migration for new fields) | Requires connection pool management |
| `EXPLAIN ANALYZE` for query tuning | Heavier than SQLite for single-user dev |
| Excellent full-text search | N/A for this use case, but available |

**Note on SQLite**: Kept for development. `create_database()` factory selects the engine based on `DATABASE_URL`. The same repository code runs on both.

---

## DD-10 · Circuit Breaker for Yahoo Finance

**Problem**

Yahoo Finance is an unofficial, free API with no SLA. It fails unpredictably. Without protection:
- 50 queued jobs all wait 30s for timeout simultaneously.
- Workers tie up for 25 minutes waiting on a dead API.
- Recovery is slow: jobs must be re-queued manually.

**Alternatives Considered**

1. **Just retry with backoff** — Retries still block workers during backoff delays.
2. **Timeout only** — Workers free up after 30s, but 50 jobs × 30s = 25min of wasted worker time.
3. **Circuit breaker** — Fast-fail after threshold; recovery probe after timeout.
4. **External market data provider (paid)** — Alpha Vantage, Polygon.io. Adds cost and dependency.

**Decision: Circuit breaker (custom, `backend/app/utils/retry.py`)**

```
CLOSED  → (5 failures) → OPEN → (60s) → HALF_OPEN → (probe) → CLOSED
```

**Tradeoffs**

| Pro | Con |
|---|---|
| Fast-fail: jobs fail in microseconds when circuit open | Circuit may open during brief transient failure |
| Workers freed immediately, can process non-Yahoo jobs | Requires tuning (threshold=5, recovery=60s) |
| Self-healing: probes automatically when ready | State lost on restart (acceptable — Redis not needed) |
| Observable: `/sre/circuit-breakers` shows state | Does not fix the underlying Yahoo reliability problem |

---

## DD-11 · Feature Flags (Redis-backed, not config file)

**Problem**

We need to disable features in production without:
1. A new deployment (deployment takes 5 minutes).
2. Modifying environment variables (requires container restart).
3. Code changes (require PR review and CI).

**Alternatives Considered**

1. **Config file (`flags.json`)** — Requires file system access in containers; not shared across replicas.
2. **Database table** — Works, but DB write per flag check adds latency to every request.
3. **LaunchDarkly / Flagsmith** — Managed service, $200+/month, external dependency.
4. **Redis hash** — Sub-millisecond, shared across all replicas, survives replica restarts.

**Decision: Redis hash with 24h TTL, env-var fallback**

```python
DEFAULTS = {
    "ENABLE_CACHE": bool(os.getenv("ENABLE_CACHE", "true")),
    "ENABLE_WORKERS": bool(os.getenv("ENABLE_WORKERS", "true")),
    "ENABLE_SCHEDULER": bool(os.getenv("ENABLE_SCHEDULER", "true")),
}
```

If Redis is unavailable, flags fall back to env vars. If env vars are unset, defaults are `true`.

**Tradeoffs**

| Pro | Con |
|---|---|
| Change takes effect within one request (no restart) | Redis goes down → env-var defaults kick in |
| Shared across all replicas instantly | TTL means flags reset after 24h (document this) |
| Auditable via `/sre/feature-flags` | No audit log of who changed which flag |
| Works without Redis (graceful degradation) | Not a full feature flag service (no targeting/rollout %) |

---

## Summary Table

| ID | Decision | Key reason |
|---|---|---|
| DD-01 | FastAPI | Pydantic validation + ASGI async |
| DD-02 | SQLAlchemy Core | SQL control without N+1 risk |
| DD-03 | Redis (multi-role) | One service: cache, queue, flags, DLQ |
| DD-04 | JWT access+refresh | Stateless, horizontal scaling |
| DD-05 | Repository pattern | SQL discoverability + testability |
| DD-06 | RQ over Celery | Simpler; Redis already present |
| DD-07 | React + Vite | Ecosystem + SPA sufficient |
| DD-08 | Docker Compose | Reproducible environment |
| DD-09 | PostgreSQL | Row-level locks, jsonb |
| DD-10 | Circuit breaker | Protect workers from Yahoo outages |
| DD-11 | Redis feature flags | Sub-ms, no deployment required |
