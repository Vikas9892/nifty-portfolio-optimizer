# Low-Level Design — Nifty Portfolio Optimizer

> Version: 4.0.0 · Last updated: 2026-07-02

This document explains the design patterns used in the codebase — what each pattern is, where it lives, and **why it was the right choice** for this problem.

---

## Table of Contents

1. [Repository Pattern](#1-repository-pattern)
2. [Service Layer](#2-service-layer)
3. [Dependency Injection](#3-dependency-injection)
4. [Context API (Frontend)](#4-context-api-frontend)
5. [Custom Hooks (Frontend)](#5-custom-hooks-frontend)
6. [Data Transfer Objects (DTOs)](#6-data-transfer-objects-dtos)
7. [Pydantic Models](#7-pydantic-models)
8. [Middleware](#8-middleware)
9. [Factory Pattern](#9-factory-pattern)
10. [Singleton Pattern](#10-singleton-pattern)
11. [Strategy Pattern](#11-strategy-pattern)
12. [Circuit Breaker Pattern](#12-circuit-breaker-pattern)

---

## 1. Repository Pattern

**Where:** `backend/app/repositories/`

```
backend/app/repositories/
├── user_repository.py       # UserRepository
├── portfolio_repository.py  # PortfolioRepository
├── job_repository.py        # JobRepository
└── market_repository.py     # MarketDataRepository
```

**What it is:** A layer that mediates between the domain (services) and the data-mapping layer (SQLAlchemy). All database queries live inside repositories — nowhere else.

**Example:**
```python
class UserRepository:
    def __init__(self, db: Database):
        self._db = db

    def get_by_email(self, email: str) -> dict | None:
        query = users.select().where(users.c.email == email)
        row = self._db.fetch_one(query)
        return dict(row) if row else None

    def create(self, name: str, email: str, password_hash: str) -> int:
        query = users.insert().values(name=name, email=email,
                                       password_hash=password_hash)
        return self._db.execute(query)
```

**Why this project needed it:**

1. **Testability** — Unit tests mock the repository, not SQLAlchemy. Services become testable with a simple `UserRepository(mock_db)`.
2. **Database portability** — We switch between SQLite (dev) and PostgreSQL (prod) by changing the connection string, not the query code. The repository abstracts the dialect.
3. **Single responsibility** — `AuthService` handles bcrypt + JWT logic. It doesn't know what table columns are called. That's the repository's job.
4. **Query discoverability** — Every SQL query in the system is in one folder. When performance problems arise, you know exactly where to look.

**Alternative considered:** ORM (SQLAlchemy ORM with model classes). Rejected because SQLAlchemy Core gives us SQL-level control without the N+1 surprises common in ORM relationships.

---

## 2. Service Layer

**Where:** `backend/app/services/`

```
backend/app/services/
├── auth_service.py         # register, login, refresh
├── portfolio_service.py    # optimize, save, list
├── job_service.py          # create, update status, lifecycle
├── market_service.py       # fetch prices, cache, circuit breaker
├── cache_service.py        # Redis cache-aside
├── feature_flags.py        # runtime toggles
├── distributed_lock.py     # Redis SET NX EX
└── dlq_service.py          # dead letter queue
```

**What it is:** The service layer contains all business logic. It sits between the HTTP routers (thin, no logic) and the repositories (thin, only SQL).

**Example:**
```python
class AuthService:
    def __init__(self, user_repo: UserRepository):
        self._repo = user_repo

    def login(self, email: str, password: str) -> TokenPair:
        user = self._repo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=401)
        if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            raise HTTPException(status_code=401)
        return self._issue_tokens(user["id"])
```

**Why:**

1. **Routers stay thin** — A router's only job is HTTP: parse request, call service, return response. It should never contain `if password not in db` logic.
2. **Reusability** — `AuthService.login()` can be called by the REST router, a CLI script, or a test, all without HTTP context.
3. **Composability** — `PortfolioService` depends on `MarketService` and `JobService`. Composing services is clean because none of them know about HTTP.

---

## 3. Dependency Injection

**Where:** `backend/app/dependencies.py`, `backend/main.py`

**What it is:** FastAPI's `Depends()` system injects shared objects (DB connection, current user, repositories) into route handlers.

**Example:**
```python
# dependencies.py
def get_db() -> Database:
    return Database(settings.database_url)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db)
) -> dict:
    payload = jwt.decode(token, settings.secret_key)
    user = UserRepository(db).get_by_id(payload["sub"])
    if not user:
        raise HTTPException(401)
    return user

# router
@router.get("/portfolio")
async def get_portfolio(user: dict = Depends(get_current_user)):
    ...
```

**Why:**

1. **No global state** — Each request gets its own DB connection, avoiding connection-sharing bugs under concurrency.
2. **Testable** — Tests call `app.dependency_overrides[get_current_user] = lambda: fake_user`. Zero test setup beyond that.
3. **Composable** — `get_current_user` itself uses `get_db`. FastAPI resolves the full dependency graph automatically.
4. **Clean separation** — Auth logic lives in `get_current_user`, not scattered in every handler.

---

## 4. Context API (Frontend)

**Where:** `frontend/src/context/`

```
frontend/src/context/
├── AuthContext.tsx      # user, tokens, login(), logout()
└── PortfolioContext.tsx # portfolios, selectedPortfolio, refresh()
```

**What it is:** React's Context API propagates shared state down the component tree without prop-drilling.

**Example:**
```tsx
export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokens] = useState<TokenPair | null>(
    () => JSON.parse(localStorage.getItem("tokens") ?? "null")
  );

  const login = async (email: string, password: string) => {
    const data = await authApi.login(email, password);
    setTokens(data);
    setUser(data.user);
  };

  return (
    <AuthContext.Provider value={{ user, tokens, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
```

**Why:**

1. **No prop-drilling** — `Navbar`, `Dashboard`, and `PortfolioCard` all need `user`. Without context, this would pass through 4 levels of props.
2. **Single source of truth** — Token refresh updates one place; all components re-render correctly.
3. **Persistence** — `useState` initializer reads from `localStorage`, so tokens survive page reloads without redundant API calls.

**Alternative considered:** Redux. Rejected — the app's state is shallow (user + portfolios). Redux would add boilerplate (actions, reducers, selectors) with no benefit at this scale.

---

## 5. Custom Hooks (Frontend)

**Where:** `frontend/src/hooks/`

```
frontend/src/hooks/
├── useAuth.ts          # wraps AuthContext, throws if outside provider
├── usePortfolio.ts     # portfolio CRUD + polling
├── useOptimize.ts      # mutation + job polling
└── useJobPoller.ts     # generic job status polling (2s interval)
```

**What it is:** Custom hooks extract stateful logic (API calls, polling, error handling) out of components into reusable functions.

**Example:**
```tsx
function useJobPoller(jobId: string | null) {
  const [job, setJob] = useState<Job | null>(null);

  useEffect(() => {
    if (!jobId) return;
    const interval = setInterval(async () => {
      const j = await jobApi.get(jobId);
      setJob(j);
      if (j.status === "completed" || j.status === "failed") {
        clearInterval(interval);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [jobId]);

  return job;
}
```

**Why:**

1. **Components stay declarative** — `OptimizeButton` renders based on job state; it doesn't contain polling logic.
2. **Reusability** — `useJobPoller` is used by both the optimize flow and the market refresh status display.
3. **Cleanup** — The `useEffect` cleanup (`clearInterval`) is co-located with the effect, making memory leaks impossible to miss.

---

## 6. Data Transfer Objects (DTOs)

**Where:** `backend/app/schemas/` (Pydantic request/response models)

**What it is:** DTOs are simple data containers that cross layer boundaries. In this project, Pydantic models serve as DTOs for HTTP request and response bodies.

**Example:**
```python
# Request DTO — what the client sends
class OptimizeRequest(BaseModel):
    tickers: list[str]
    start: str
    end: str
    risk_free_rate: float = 0.05
    max_weight: float = Field(default=0.30, ge=0.01, le=1.0)

# Response DTO — what the API returns
class OptimizeResponse(BaseModel):
    job_id: str
    status: str
    weights: dict[str, float] | None = None
    sharpe_ratio: float | None = None
    expected_return: float | None = None
    volatility: float | None = None
```

**Why:**

1. **Type safety at boundaries** — Input validated at entry point; downstream code never receives `tickers=None`.
2. **Self-documenting API** — FastAPI generates OpenAPI schema from these models automatically.
3. **Decoupling** — The DB schema (snake_case columns) differs from the API schema (camelCase responses). DTOs let both sides evolve independently.

---

## 7. Pydantic Models

**Where:** `backend/app/core/config.py`, `backend/app/schemas/`

**What it is:** Pydantic's `BaseModel` and `BaseSettings` provide runtime validation and parsing for configs and HTTP models.

**Example — Settings:**
```python
class Settings(BaseSettings):
    secret_key: str = "dev-secret-change-in-prod"
    database_url: str = "sqlite:///./data/portfolio.db"
    redis_url: str = ""
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

**Why Pydantic:**

1. **`model_validator`** — Pydantic v2 validators run at startup, catching `DATABASE_URL=` typos before the first request.
2. **Coercion** — `"30"` from `.env` is automatically cast to `int`. No manual `int(os.getenv(...))` chains.
3. **`model_dump()`** — Returns a plain `dict`, making serialization trivial for JSON responses.
4. **Performance** — Pydantic v2 (Rust core) validates our 5-field request in ~0.003ms (see benchmarks).

---

## 8. Middleware

**Where:** `backend/main.py`, `backend/app/middleware/`

```python
# Correlation ID — injected before any handler runs
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# CORS — allows React dev server (localhost:3000) to call API
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, ...)
```

**Why middleware (not decorators):**

1. **Cross-cutting concerns** — Correlation IDs, CORS, and timing apply to every endpoint. Middleware ensures no endpoint can forget to add them.
2. **Order control** — Middleware runs in stack order. Correlation ID middleware runs before auth, so logs always have a request ID even for 401s.
3. **No repetition** — 20 routes don't each need `@add_cors_headers`. One middleware handles all 20.

---

## 9. Factory Pattern

**Where:** `backend/app/db/database.py`

**What it is:** A factory encapsulates object creation. Instead of callers `new Database(...)` with all connection params, a factory function builds the right DB object based on config.

**Example:**
```python
def create_database(url: str) -> Database:
    if url.startswith("sqlite"):
        return Database(url, connect_args={"check_same_thread": False})
    elif url.startswith("postgresql"):
        return Database(url, min_size=2, max_size=10)
    else:
        raise ValueError(f"Unsupported database URL: {url}")

db = create_database(settings.database_url)
```

**Why:**

1. **Environment transparency** — Dev uses SQLite, prod uses PostgreSQL. The rest of the codebase calls `db.fetch_one(query)` without knowing which.
2. **Testability** — Tests call `create_database("sqlite:///:memory:")` to get an in-memory DB, no mocking required.
3. **Configuration centralized** — Connection pool sizes, timeouts, and per-dialect options are set in one place.

---

## 10. Singleton Pattern

**Where:** `backend/app/services/cache_service.py`, `backend/app/services/dlq_service.py`, `backend/app/services/feature_flags.py`

**What it is:** A singleton ensures a class has only one instance for the lifetime of the application. In this project, service singletons are created at module import time.

**Example:**
```python
# cache_service.py
class CacheService:
    def __init__(self):
        self._client: redis.Redis | None = None

    def _get_client(self):
        if self._client is None:
            url = os.getenv("REDIS_URL", "")
            if url:
                self._client = redis.from_url(url)
        return self._client

cache = CacheService()  # ← singleton, imported by other modules
```

**Why:**

1. **Connection reuse** — Creating a Redis connection per request would exhaust the connection pool. One shared client multiplexes all requests.
2. **Feature flag consistency** — If `FeatureFlags` were per-request, flag values could differ between the check and the action within one request.
3. **Simplicity** — FastAPI's DI can also manage lifecycles, but for stateless services (cache, DLQ) that have no per-request state, module-level singletons are idiomatic Python and require no framework wiring.

---

## 11. Strategy Pattern

**Where:** `backend/app/services/portfolio_service.py`

**What it is:** The Strategy pattern defines a family of algorithms, encapsulates each, and makes them interchangeable. The optimizer uses this to support multiple optimization objectives.

**Example:**
```python
class OptimizationStrategy(Protocol):
    def optimize(self, mu, sigma) -> dict[str, float]: ...

class MaxSharpeStrategy:
    def optimize(self, mu, sigma) -> dict[str, float]:
        ef = EfficientFrontier(mu, sigma)
        ef.max_sharpe()
        return ef.clean_weights()

class MinVolatilityStrategy:
    def optimize(self, mu, sigma) -> dict[str, float]:
        ef = EfficientFrontier(mu, sigma)
        ef.min_volatility()
        return ef.clean_weights()

class PortfolioOptimizer:
    def __init__(self, strategy: OptimizationStrategy = MaxSharpeStrategy()):
        self._strategy = strategy

    def run(self, prices: pd.DataFrame) -> dict:
        mu = expected_returns.mean_historical_return(prices)
        sigma = risk_models.sample_cov(prices)
        return self._strategy.optimize(mu, sigma)
```

**Why:**

1. **Open/closed principle** — Adding `MaxReturnStrategy` or `RiskParityStrategy` requires zero changes to `PortfolioOptimizer` — just a new class.
2. **Runtime selection** — The API can accept `objective: "max_sharpe" | "min_vol"` and select the strategy from a registry, with no `if/elif` chains in the service.
3. **Testability** — Each strategy is independently testable with fixed inputs, deterministic outputs.

---

## 12. Circuit Breaker Pattern

**Where:** `backend/app/utils/retry.py`

**What it is:** Wraps an external call with state machine logic. If failures exceed a threshold, the circuit "opens" and subsequent calls fail fast instead of waiting for a timeout.

**States:**
```
CLOSED ──(failure_count >= threshold)──▶ OPEN
OPEN   ──(recovery_timeout elapsed)───▶ HALF_OPEN
HALF_OPEN ──(probe succeeds)──────────▶ CLOSED
HALF_OPEN ──(probe fails)─────────────▶ OPEN
```

**Example:**
```python
class CircuitBreaker:
    def __init__(self, name, failure_threshold=5, recovery_timeout=60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"
        self.opened_at: float | None = None

    def call(self, fn, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.opened_at > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError(self.name)
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

yahoo_breaker = register_breaker(
    CircuitBreaker("yahoo_finance", failure_threshold=5, recovery_timeout=60)
)
```

**Why:**

1. **Protects resources** — Without it, 50 portfolio jobs in the queue all wait 30s for Yahoo Finance timeouts when the API is down. The circuit opens after 5 failures, letting all subsequent jobs fail in microseconds.
2. **Allows recovery** — The HALF_OPEN state probes the dependency without letting traffic flood through. One probe, not 50 simultaneous ones.
3. **Observability** — Circuit state is exposed via `GET /api/v1/sre/circuit-breakers` so on-call engineers can see what's open without digging through logs.

---

## Pattern Interaction Map

```
  HTTP Request
      │
      ▼
  Middleware (Cross-cutting: CORS, CorrelationID, Timing)
      │
      ▼
  Router (thin, no logic)
      │
      ▼  Depends()
  DI (inject: db, current_user, repositories)
      │
      ▼
  Service Layer (business logic, Strategy for optimization)
      │      │
      │      ├─ CacheService (Singleton, cache-aside)
      │      ├─ FeatureFlags (Singleton, Redis-backed)
      │      └─ CircuitBreaker (State machine, wraps Yahoo calls)
      │
      ▼
  Repository Layer (SQL queries only)
      │
      ▼
  Database (SQLite dev / PostgreSQL prod, via Factory)

  Frontend:
  AuthContext (Singleton per app tree) → useAuth (hook) → Component
  PortfolioContext                     → usePortfolio    → Component
  DTO (Pydantic) validates at API boundary before entering services
```
