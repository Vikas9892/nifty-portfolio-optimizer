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

    # Database
    database_url: str = "data/portfolio.db"

    # Rate limiting
    rate_limit_login: str = "5/minute"
    rate_limit_register: str = "3/minute"
    rate_limit_optimize: str = "10/minute"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
