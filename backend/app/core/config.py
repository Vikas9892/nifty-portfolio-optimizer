from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Nifty Portfolio Optimizer"
    environment: str = "development"

    # JWT
    jwt_secret_key: str = "change-me-generate-a-real-secret-before-deploying"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Database — "sqlite:///path" or "postgresql://user:pass@host/db"
    database_url: str = "sqlite:///data/portfolio.db"

    # Redis — optional; app degrades gracefully when absent
    redis_url: str = ""

    # CORS — comma-separated origins or JSON list
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:80",
        "http://localhost",
    ]

    # Rate limiting
    rate_limit_login: str = "5/minute"
    rate_limit_register: str = "3/minute"
    rate_limit_optimize: str = "10/minute"

    # ── Phase 8: Background jobs ──────────────────────────────────────────────
    job_queue_name: str = "optimize"
    job_ttl_seconds: int = 3600  # how long job data lives in Redis

    # ── Phase 8: Scheduler ───────────────────────────────────────────────────
    scheduler_enabled: bool = True
    # NSE closes 15:30 IST; data available ~13:30 UTC
    market_refresh_hour: int = 13
    market_refresh_minute: int = 30

    # ── Phase 8: Resilience ──────────────────────────────────────────────────
    yahoo_retry_attempts: int = 3
    yahoo_retry_wait_min: float = 1.0
    yahoo_retry_wait_max: float = 10.0
    circuit_breaker_fail_max: int = 5
    circuit_breaker_reset_timeout: int = 60  # seconds before OPEN → HALF_OPEN

    # ── Phase 8: Connection pool (PostgreSQL only) ───────────────────────────
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # ── Phase 8: Role-based rate limits (reqs/minute) ────────────────────────
    rate_limit_optimize_user: int = 10
    rate_limit_optimize_premium: int = 100

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def has_redis(self) -> bool:
        return bool(self.redis_url)


settings = Settings()
