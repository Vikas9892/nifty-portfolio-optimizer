from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.middleware.logging_middleware import RequestLoggingMiddleware
from backend.app.middleware.request_id_middleware import RequestIDMiddleware
from backend.app.models.database import init_all_tables
from backend.app.models.db import get_engine
from backend.app.routers import admin, auth, benchmark, jobs, portfolio, sre, stocks
from backend.app.schemas.response import ErrorResponse
from backend.app.utils.exceptions import AppException
from backend.app.utils.logger import logger

# ── Rate limiter (shared across routers) ─────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("STARTUP | Initialising database tables…")
    init_all_tables()

    # Phase 8: Prometheus instrumentation
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/health", "/ready", "/metrics"],
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        logger.info("STARTUP | Prometheus /metrics endpoint registered")
    except Exception as exc:
        logger.warning("STARTUP | Prometheus not available: %s", exc)

    # Phase 8: APScheduler for market data refresh
    scheduler = None
    if settings.scheduler_enabled:
        try:
            from backend.app.services.scheduler import start_scheduler

            scheduler = start_scheduler(
                hour=settings.market_refresh_hour,
                minute=settings.market_refresh_minute,
            )
        except Exception as exc:
            logger.warning("STARTUP | Scheduler not started: %s", exc)

    logger.info("STARTUP | %s v4.0.0 ready (%s)", settings.app_name, settings.environment)
    yield

    # Shutdown
    if scheduler:
        from backend.app.services.scheduler import stop_scheduler

        stop_scheduler()
    logger.info("SHUTDOWN | Goodbye.")


# ── Application factory ───────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description=(
        "Production-grade REST API for Nifty 50 mean-variance portfolio optimization.\n\n"
        "**Authentication:** JWT Bearer tokens. Register → Login → use `access_token` in the "
        "`Authorization: Bearer <token>` header on every protected endpoint.\n\n"
        "**Versioning:** All endpoints are under `/api/v1/`.\n\n"
        "**Async jobs:** POST `/api/v1/jobs/optimize` → returns `job_id` → "
        "poll `GET /api/v1/jobs/{job_id}` for result.\n\n"
        "**SRE:** Feature flags, circuit breaker states, and DLQ management under `/api/v1/sre/`."
    ),
    version="4.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware (applied bottom-up — last added = outermost wrap) ──────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)  # innermost — sets request_id first
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# ── Global exception handlers ─────────────────────────────────────────────────
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    rid = getattr(request.state, "request_id", "-")
    logger.warning(
        "req_id=%s APP_ERROR | %s %s → %s: %s",
        rid,
        request.method,
        request.url.path,
        exc.error_code,
        exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=exc.message, error_code=exc.error_code).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    rid = getattr(request.state, "request_id", "-")
    logger.error(
        "req_id=%s UNHANDLED | %s %s → %s",
        rid,
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            message="An unexpected error occurred. Please try again later.",
            error_code="INTERNAL_SERVER_ERROR",
        ).model_dump(),
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(portfolio.router)
app.include_router(stocks.router)
app.include_router(benchmark.router)
app.include_router(jobs.router)  # Phase 8: async job endpoints
app.include_router(admin.router)  # Phase 8: metrics dashboard
app.include_router(sre.router)  # Phase 9: circuit breakers / feature flags / DLQ


# ── Observability endpoints ───────────────────────────────────────────────────


@app.get("/", tags=["Health"], summary="Root", include_in_schema=False)
@app.get("/health", tags=["Health"], summary="Liveness probe")
def health():
    """Returns 200 as long as the process is alive."""
    return {"status": "healthy", "service": settings.app_name, "version": "4.0.0"}


@app.get("/ready", tags=["Health"], summary="Readiness probe")
def ready():
    """Returns 200 if the DB is reachable (used by container orchestrators)."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as exc:
        logger.error("READINESS_FAILED | %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "db": "unreachable"},
        )


@app.get("/version", tags=["Health"], summary="Build version")
def version():
    """Returns the current API version and runtime environment."""
    return {
        "version": "4.0.0",
        "environment": settings.environment,
        "python": __import__("platform").python_version(),
        "features": ["async-jobs", "prometheus", "scheduler", "circuit-breaker", "retry"],
    }
