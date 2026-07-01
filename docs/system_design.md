# System Design — Nifty Portfolio Optimizer

> Version: 4.0.0 · Last updated: 2026-07-02

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Component Map](#2-component-map)
3. [Request Flow — Portfolio Optimize](#3-request-flow--portfolio-optimize)
4. [Authentication Flow](#4-authentication-flow)
5. [Refresh Token Flow](#5-refresh-token-flow)
6. [Background Job Flow](#6-background-job-flow)
7. [Scheduler Flow](#7-scheduler-flow)
8. [Sequence Diagrams](#8-sequence-diagrams)
   - [8.1 Login](#81-login-sequence)
   - [8.2 Optimize](#82-optimize-sequence)
   - [8.3 Refresh Token](#83-refresh-token-sequence)
   - [8.4 Scheduler](#84-scheduler-sequence)
   - [8.5 Background Worker](#85-background-worker-sequence)
   - [8.6 Portfolio Save](#86-portfolio-save-sequence)
   - [8.7 Dead Letter Queue](#87-dead-letter-queue-sequence)
   - [8.8 Retry / Circuit Breaker](#88-retry--circuit-breaker-sequence)

---

## 1. High-Level Architecture

```
                         ┌─────────────────────────────────────────────────────┐
                         │                  PRODUCTION STACK                   │
                         └─────────────────────────────────────────────────────┘

 ┌──────────┐    HTTPS    ┌──────────────┐   HTTP/1.1   ┌──────────────────────┐
 │  Browser │────────────▶│  Nginx/LB    │─────────────▶│   React SPA (Vite)   │
 │  Mobile  │            │  (Port 80/443)│              │   Port 3000           │
 └──────────┘            └──────────────┘               └──────────────────────┘
       │                        │                                  │
       │                        │ /api/*  reverse proxy            │  XHR/Fetch
       │                        ▼                                  │
       │               ┌─────────────────┐                         │
       └───────────────│  FastAPI (ASGI)  │◀────────────────────────┘
                       │  Uvicorn workers│
                       │  Port 8000       │
                       └────────┬────────┘
                                │
              ┌─────────────────┼──────────────────┐
              │                 │                  │
              ▼                 ▼                  ▼
   ┌──────────────────┐ ┌────────────┐  ┌─────────────────┐
   │  Auth Service    │ │  Portfolio │  │  Market Service  │
   │  - bcrypt hash   │ │  Optimizer │  │  - Yahoo Finance │
   │  - JWT sign/vfy  │ │  - PyPfOpt │  │  - Circuit Bkr  │
   └──────────────────┘ └────────────┘  └─────────────────┘
              │                 │                  │
              └────────────┬────┘                  │
                           ▼                       │
              ┌─────────────────────────────────┐  │
              │       Repository Layer          │  │
              │  UserRepo / PortfolioRepo /     │  │
              │  JobRepo  / MarketDataRepo      │  │
              └────────────┬────────────────────┘  │
                           │                       │
              ┌────────────┼────────────┐          │
              ▼            ▼            ▼          ▼
    ┌─────────────┐ ┌──────────┐ ┌──────────────────┐
    │ PostgreSQL  │ │  SQLite  │ │  Redis           │
    │ (prod)      │ │ (dev)    │ │  - Job Queue     │
    │ Port 5432   │ │          │ │  - Cache (24h)   │
    └─────────────┘ └──────────┘ │  - Feature Flags │
                                 │  - DLQ           │
                                 │  - Dist Lock     │
                                 └────────┬─────────┘
                                          │ RQ workers
                                          ▼
                          ┌───────────────────────────┐
                          │  Background Worker (RQ)   │
                          │  - portfolio_optimize_task│
                          │  - market_refresh_task    │
                          └───────────────────────────┘
                                          │ yfinance
                                          ▼
                               ┌──────────────────┐
                               │  Yahoo Finance   │
                               │  (External API)  │
                               └──────────────────┘

  Observability stack:
  ┌────────────────┐  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐
  │  Prometheus    │  │  Grafana    │  │ Alertmanager │  │  JSON Logs  │
  │  /metrics      │─▶│  Dashboards │  │  Email/Slack │  │  (stdout)   │
  └────────────────┘  └─────────────┘  └──────────────┘  └─────────────┘
```

---

## 2. Component Map

| Layer | Technology | Responsibility |
|---|---|---|
| Reverse Proxy | Nginx | TLS termination, static file serving, upstream proxy |
| Frontend | React 18 + Vite + TypeScript | SPA — auth, portfolio UI, charts |
| API Gateway | FastAPI 0.111 + Uvicorn | HTTP routing, middleware, OpenAPI |
| Auth | python-jose + bcrypt | JWT access/refresh tokens, password hashing |
| Services | Pure Python classes | Business logic, validation, orchestration |
| Repositories | SQLAlchemy Core | Database I/O, query building, no ORM overhead |
| Cache | Redis (via redis-py) | Cache-aside for market data; TTL = 24h |
| Queue | Redis + RQ | Async job queue; workers pull from `default` queue |
| Database | PostgreSQL (prod) / SQLite (dev) | Persistent state |
| Scheduler | APScheduler | Periodic market refresh every 15 min |
| Observability | Prometheus + Grafana | Metrics, dashboards, alert rules |

---

## 3. Request Flow — Portfolio Optimize

```
User Browser
    │
    │ POST /api/v1/portfolio/optimize
    │ Header: Authorization: Bearer <access_token>
    │
    ▼
Nginx (port 443)
    │
    │ proxy_pass http://backend:8000
    │
    ▼
FastAPI — ASGI event loop
    │
    ├─ 1. CorrelationID Middleware
    │      generates X-Request-ID: uuid4, attaches to request state
    │
    ├─ 2. Auth Middleware / Depends(get_current_user)
    │      decodes JWT, loads user_id from sub claim
    │      raises 401 if expired or invalid
    │
    ├─ 3. Request Router → portfolio_router.optimize()
    │
    ├─ 4. Idempotency check
    │      key = hash(user_id + tickers + start + end)
    │      if cache.get(key) → return existing job immediately
    │
    ├─ 5. Create Job record in DB (status=PENDING)
    │
    ├─ 6. Enqueue RQ task  ──────────────────────────────────────┐
    │      rq.enqueue(portfolio_optimize_task, job_id)            │
    │                                                             │
    ├─ 7. Return 202 Accepted { job_id, status: "pending" }      │
    │                                                             │
    ▼                                                             ▼
Client polls GET /api/v1/jobs/{job_id}            RQ Worker Process
                                                       │
                                                       ├─ 1. Load job from DB
                                                       ├─ 2. mark_running()
                                                       ├─ 3. Check cache for prices
                                                       │      if miss → yfinance.download()
                                                       │      if yahoo down → CircuitBreaker opens
                                                       ├─ 4. Run PyPfOpt (EfficientFrontier)
                                                       ├─ 5. Store weights in DB
                                                       ├─ 6. mark_completed()
                                                       └─ 7. Cache result (TTL=300s)

Client polling response:
  PENDING → RUNNING → COMPLETED → weights, sharpe, return, volatility
```

---

## 4. Authentication Flow

```
                    ┌─────────┐         ┌──────────┐        ┌──────────┐
                    │  React  │         │  FastAPI │        │    DB    │
                    └────┬────┘         └────┬─────┘        └────┬─────┘
                         │                   │                    │
  POST /auth/register    │                   │                    │
  { name, email, pw }   │──────────────────▶│                    │
                         │                   │                    │
                         │        validate Pydantic schema        │
                         │                   │                    │
                         │        bcrypt.hashpw(pw, rounds=12)    │
                         │                   │                    │
                         │                   │ INSERT INTO users  │
                         │                   │──────────────────▶│
                         │                   │                    │
                         │  201 { message }  │                    │
                         │◀──────────────────│                    │
                         │                   │                    │
  POST /auth/login       │                   │                    │
  { email, password }    │──────────────────▶│                    │
                         │                   │ SELECT user        │
                         │                   │──────────────────▶│
                         │                   │◀──────────────────│
                         │                   │                    │
                         │        bcrypt.checkpw(pw, hash)        │
                         │        if wrong → 401                  │
                         │                   │                    │
                         │        JWT encode { sub: user_id,      │
                         │                    type: "access",     │
                         │                    exp: now+30min }    │
                         │        JWT encode { sub: user_id,      │
                         │                    type: "refresh",    │
                         │                    exp: now+7days }    │
                         │                   │                    │
                         │  200 { access_token, refresh_token,   │
                         │         expires_in: 1800 }             │
                         │◀──────────────────│                    │
                         │                   │                    │
  Subsequent requests:   │                   │                    │
  Authorization: Bearer <access_token>       │                    │
                         │──────────────────▶│                    │
                         │         JWT.decode() → user_id         │
                         │         Depends(get_current_user)      │
                         │◀──────────────────│                    │
```

---

## 5. Refresh Token Flow

```
  ┌─────────┐                    ┌──────────┐
  │  React  │                    │  FastAPI │
  └────┬────┘                    └────┬─────┘
       │                              │
       │  access_token expires (401)  │
       │◀─────────────────────────────│
       │                              │
       │  POST /auth/refresh          │
       │  { refresh_token }           │
       │─────────────────────────────▶│
       │                              │
       │              JWT.decode(refresh_token)
       │              assert type == "refresh"
       │              assert not expired (7 days)
       │                              │
       │              Issue new access_token (30 min)
       │              Issue new refresh_token (7 days)   ← token rotation
       │                              │
       │  200 { access_token,         │
       │         refresh_token }      │
       │◀─────────────────────────────│
       │                              │
       │  Retry original request      │
       │─────────────────────────────▶│
```

*Token rotation prevents refresh token theft: each refresh issues a new pair. Stolen old refresh tokens become invalid after the first use.*

---

## 6. Background Job Flow

```
  FastAPI handler                 Redis (RQ Queue)              RQ Worker
       │                               │                            │
       │ rq.enqueue(task, job_id) ────▶│                            │
       │                               │  LPUSH rq:queue:default    │
       │ return 202 { job_id }         │                            │
       │                               │ BLPOP (blocking pop)  ────▶│
       │                               │                            │
       │                               │                 Load job from DB
       │                               │                 mark_running()
       │                               │                            │
       │                               │              yfinance.download()
       │                               │              [Circuit breaker guards]
       │                               │                            │
       │                               │              PyPfOpt optimize
       │                               │                            │
       │                               │              save weights to DB
       │                               │              mark_completed()
       │                               │                            │
  GET /jobs/{id} ─────────────────────────────────────────────────▶│
  polling                             │              { status, weights, sharpe }
       │◀───────────────────────────────────────────────────────────│

  Failure path:
       │                               │                            │
       │                               │              job fails → increment_retry()
       │                               │              if retry < 3 → re-enqueue
       │                               │              if retry ≥ 3 → mark_dead()
       │                               │                          → dlq.push(job)
       │                               │                            │
  GET /api/v1/sre/dlq                 │              DLQ stores snapshot
  (admin endpoint)                    │              7-day TTL
```

---

## 7. Scheduler Flow

```
  APScheduler (main process)        Redis (Distributed Lock)      DB + Yahoo
       │                                    │                          │
       │  Every 15 minutes:                 │                          │
       │                                    │                          │
       │  acquire_lock("market-refresh",    │                          │
       │               ttl=600)             │                          │
       │───────────────────────────────────▶│                          │
       │              SET market-refresh NX EX 600                    │
       │                                    │                          │
       │  if NOT acquired (another          │                          │
       │  replica holds lock) → skip        │                          │
       │                                    │                          │
       │  if acquired:                      │                          │
       │    for each symbol in NIFTY50:    │                          │
       │      yfinance.download(symbol)    │───────────────────────────▶
       │      cache.set(symbol, data)      │                          │
       │      save to market_data table    │                          │
       │    end for                        │                          │
       │                                   │                          │
       │  release_lock() ─────────────────▶│                          │
       │              DEL market-refresh (Lua compare-and-delete)     │
       │                                   │                          │

  Why distributed lock:
  In a multi-replica deployment (3x FastAPI pods), all schedulers
  fire at the same minute. Without the lock, all 3 pods would hit
  Yahoo Finance simultaneously for all 50 symbols → 150 API calls
  instead of 50. The lock ensures exactly one pod runs the refresh.
```

---

## 8. Sequence Diagrams

### 8.1 Login Sequence

```mermaid
sequenceDiagram
    actor User
    participant React
    participant FastAPI
    participant DB

    User->>React: Enter email + password
    React->>FastAPI: POST /api/v1/auth/login {email, password}
    FastAPI->>DB: SELECT * FROM users WHERE email=?
    DB-->>FastAPI: user row (or None)
    alt user not found
        FastAPI-->>React: 401 Unauthorized
    else user found
        FastAPI->>FastAPI: bcrypt.checkpw(plain, hashed)
        alt wrong password
            FastAPI-->>React: 401 Unauthorized
        else correct
            FastAPI->>FastAPI: JWT encode access_token (30 min)
            FastAPI->>FastAPI: JWT encode refresh_token (7 days)
            FastAPI-->>React: 200 {access_token, refresh_token}
            React->>React: localStorage.setItem(tokens)
        end
    end
```

### 8.2 Optimize Sequence

```mermaid
sequenceDiagram
    actor User
    participant React
    participant FastAPI
    participant Cache as Redis Cache
    participant Queue as Redis Queue
    participant Worker
    participant Yahoo as Yahoo Finance

    User->>React: Select tickers + date range → Optimize
    React->>FastAPI: POST /api/v1/portfolio/optimize {tickers, start, end}
    FastAPI->>FastAPI: Verify JWT, extract user_id
    FastAPI->>Cache: GET idempotency:{hash}
    alt cache hit (duplicate request)
        Cache-->>FastAPI: existing job
        FastAPI-->>React: 200 {job_id, status: "completed"}
    else cache miss
        FastAPI->>FastAPI: Create Job (status=PENDING)
        FastAPI->>Queue: LPUSH rq:queue:default {job_id}
        FastAPI-->>React: 202 {job_id, status: "pending"}
        loop Poll every 2s
            React->>FastAPI: GET /api/v1/jobs/{job_id}
            FastAPI-->>React: {status: "running"|"completed"|"failed"}
        end
        Worker->>Queue: BLPOP (dequeue job)
        Worker->>Worker: mark_running()
        Worker->>Cache: GET prices:{tickers}
        alt cache miss
            Worker->>Yahoo: yfinance.download(tickers)
            Yahoo-->>Worker: OHLCV DataFrame
            Worker->>Cache: SET prices:{tickers} TTL=86400
        end
        Worker->>Worker: PyPfOpt EfficientFrontier.max_sharpe()
        Worker->>FastAPI: mark_completed(weights, sharpe)
        React->>FastAPI: GET /api/v1/jobs/{job_id}
        FastAPI-->>React: {status: "completed", weights, sharpe_ratio, ...}
    end
```

### 8.3 Refresh Token Sequence

```mermaid
sequenceDiagram
    participant React
    participant Axios Interceptor
    participant FastAPI

    React->>FastAPI: GET /api/v1/portfolio (expired access token)
    FastAPI-->>React: 401 Unauthorized
    React->>Axios Interceptor: onResponseError(401)
    Axios Interceptor->>FastAPI: POST /api/v1/auth/refresh {refresh_token}
    alt refresh_token valid
        FastAPI->>FastAPI: JWT decode, verify type=refresh
        FastAPI->>FastAPI: Issue new access_token + refresh_token (rotation)
        FastAPI-->>Axios Interceptor: 200 {access_token, refresh_token}
        Axios Interceptor->>Axios Interceptor: update localStorage
        Axios Interceptor->>FastAPI: Retry original request (new token)
        FastAPI-->>React: 200 Original response
    else refresh_token expired
        FastAPI-->>Axios Interceptor: 401
        Axios Interceptor->>React: logout() → redirect /login
    end
```

### 8.4 Scheduler Sequence

```mermaid
sequenceDiagram
    participant APScheduler
    participant DistLock as Redis Distributed Lock
    participant Yahoo as Yahoo Finance
    participant Cache as Redis Cache
    participant DB

    Note over APScheduler: Fires every 15 minutes
    APScheduler->>DistLock: SET market-refresh NX EX 600
    alt Lock NOT acquired (another replica holds it)
        DistLock-->>APScheduler: nil (skip this replica)
    else Lock acquired
        DistLock-->>APScheduler: OK
        loop For each symbol in NIFTY50 watchlist
            APScheduler->>Yahoo: yfinance.download(symbol, period=1d)
            Yahoo-->>APScheduler: OHLCV data
            APScheduler->>Cache: SET market:{symbol} TTL=900
            APScheduler->>DB: UPSERT market_data
        end
        APScheduler->>DistLock: DEL market-refresh (Lua compare-and-delete)
    end
```

### 8.5 Background Worker Sequence

```mermaid
sequenceDiagram
    participant Queue as Redis Queue
    participant Worker
    participant DB
    participant Yahoo as Yahoo Finance
    participant DLQ

    Worker->>Queue: BLPOP rq:queue:default (blocking)
    Queue-->>Worker: {job_id, task_fn, args}
    Worker->>DB: UPDATE jobs SET status=RUNNING
    Worker->>Yahoo: yfinance.download(tickers)
    alt Yahoo Finance succeeds
        Yahoo-->>Worker: OHLCV DataFrame
        Worker->>Worker: PyPfOpt optimize
        Worker->>DB: UPDATE jobs SET status=COMPLETED, result=weights
    else Yahoo Finance fails
        Yahoo-->>Worker: Exception / timeout
        Worker->>DB: UPDATE jobs SET retry_count += 1
        alt retry_count < MAX_RETRIES (3)
            Worker->>Queue: Re-enqueue job (exponential backoff)
        else retry_count >= MAX_RETRIES
            Worker->>DB: UPDATE jobs SET status=DEAD
            Worker->>DLQ: dlq.push(job snapshot)
            Note over DLQ: Stored for 7 days, inspectable via /sre/dlq
        end
    end
```

### 8.6 Portfolio Save Sequence

```mermaid
sequenceDiagram
    actor User
    participant React
    participant FastAPI
    participant PortfolioRepo
    participant DB

    User->>React: Click "Save Portfolio"
    React->>FastAPI: POST /api/v1/portfolio/save {name, weights, job_id}
    FastAPI->>FastAPI: Verify JWT → user_id
    FastAPI->>PortfolioRepo: save(user_id, name, weights)
    PortfolioRepo->>DB: INSERT INTO portfolios (user_id, name, created_at)
    DB-->>PortfolioRepo: portfolio_id
    PortfolioRepo->>DB: INSERT INTO portfolio_stocks (portfolio_id, ticker, weight)
    DB-->>PortfolioRepo: OK
    PortfolioRepo-->>FastAPI: portfolio_id
    FastAPI-->>React: 201 {portfolio_id, name, created_at}
    React->>React: Show "Saved!" toast
```

### 8.7 Dead Letter Queue Sequence

```mermaid
sequenceDiagram
    participant Worker
    participant JobService
    participant DLQ as DLQ Service
    participant Redis
    participant Admin

    Worker->>JobService: increment_retry()
    JobService->>JobService: retry_count = 3 (≥ MAX_RETRIES)
    JobService->>JobService: mark_dead()
    Worker->>DLQ: dlq.push(job_snapshot)
    DLQ->>Redis: SET dlq:job:{id} snapshot TTL=604800
    DLQ->>Redis: LPUSH dlq:index job_id
    Note over DLQ, Redis: Job stored for 7 days

    Admin->>FastAPI: GET /api/v1/sre/dlq
    FastAPI-->>Admin: [{job_id, user_id, retry_count, dlq_at, error}]

    alt Admin wants to retry
        Admin->>FastAPI: POST /api/v1/sre/dlq/{job_id}/retry
        FastAPI->>DLQ: remove(job_id)
        FastAPI->>JobService: reset status → PENDING
        FastAPI-->>Admin: {status: "re-queued"}
    else Admin discards
        Admin->>FastAPI: DELETE /api/v1/sre/dlq/{job_id}
        FastAPI->>DLQ: remove(job_id)
        FastAPI-->>Admin: 204 No Content
    end
```

### 8.8 Retry / Circuit Breaker Sequence

```mermaid
sequenceDiagram
    participant Service
    participant CircuitBreaker
    participant Yahoo as Yahoo Finance

    Service->>CircuitBreaker: call(yfinance.download, ticker)
    
    alt Circuit CLOSED (healthy)
        CircuitBreaker->>Yahoo: yfinance.download(ticker)
        alt Success
            Yahoo-->>CircuitBreaker: data
            CircuitBreaker->>CircuitBreaker: failure_count = 0
            CircuitBreaker-->>Service: data
        else Failure
            Yahoo-->>CircuitBreaker: Exception
            CircuitBreaker->>CircuitBreaker: failure_count += 1
            alt failure_count >= threshold (5)
                CircuitBreaker->>CircuitBreaker: state = OPEN
                CircuitBreaker->>CircuitBreaker: opened_at = now()
            end
            CircuitBreaker-->>Service: raise Exception
        end
    else Circuit OPEN
        CircuitBreaker->>CircuitBreaker: check recovery_timeout (60s)
        alt timeout NOT elapsed
            CircuitBreaker-->>Service: raise CircuitBreakerOpen (fast fail)
        else timeout elapsed → HALF_OPEN
            CircuitBreaker->>Yahoo: probe request
            alt probe succeeds
                CircuitBreaker->>CircuitBreaker: state = CLOSED
                CircuitBreaker-->>Service: data
            else probe fails
                CircuitBreaker->>CircuitBreaker: state = OPEN (reset timer)
                CircuitBreaker-->>Service: raise CircuitBreakerOpen
            end
        end
    end
```

---

## Architecture Principles

| Principle | How it's applied |
|---|---|
| **Separation of concerns** | Router → Service → Repository → DB; no business logic in routes |
| **Fail fast** | Circuit breaker on Yahoo Finance; 60s recovery timeout |
| **Async by default** | RQ offloads CPU-bound optimization to workers; API stays <50ms |
| **Idempotency** | Cache-keyed by request hash; duplicate calls return same job |
| **Observability first** | Every request tagged with correlation ID; JSON logs; Prometheus metrics |
| **Defense in depth** | JWT auth + bcrypt + rate limiting + input validation (Pydantic) |
| **Graceful degradation** | Feature flags allow disabling workers/cache without restart |
