from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from backend.app.core.config import settings
from backend.app.middleware.logging_middleware import RequestLoggingMiddleware
from backend.app.models.database import init_all_tables
from backend.app.routers import auth, benchmark, portfolio, stocks
from backend.app.schemas.response import ErrorResponse
from backend.app.utils.exceptions import AppException
from backend.app.utils.logger import logger


# ── Rate limiter (shared across routers) ─────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("STARTUP | Initialising database tables…")
    init_all_tables()
    logger.info("STARTUP | %s v2.0.0 ready (%s)", settings.app_name, settings.environment)
    yield
    logger.info("SHUTDOWN | Goodbye.")


# ── Application factory ───────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description=(
        "Production-grade REST API for Nifty 50 mean-variance portfolio optimization.\n\n"
        "**Authentication:** JWT Bearer tokens. Register → Login → use `access_token` in the "
        "`Authorization: Bearer <token>` header on every protected endpoint.\n\n"
        "**Versioning:** All endpoints are under `/api/v1/`."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware (applied bottom-up — last added = outermost) ───────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# ── Global exception handlers ─────────────────────────────────────────────────
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning("APP_ERROR | %s %s → %s: %s",
                   request.method, request.url.path, exc.error_code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=exc.message, error_code=exc.error_code).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("UNHANDLED_ERROR | %s %s → %s", request.method, request.url.path, exc, exc_info=True)
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


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"], summary="Health check")
def health():
    return {
        "success": True,
        "message": "Nifty Portfolio Optimizer API",
        "version": "2.0.0",
        "environment": settings.environment,
        "docs": "/docs",
    }
