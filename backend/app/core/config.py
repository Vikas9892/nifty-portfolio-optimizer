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

    # Redis — optional, graceful fallback when absent
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

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()
