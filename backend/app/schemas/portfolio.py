from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, Field, field_validator, model_validator


class OptimizeRequest(BaseModel):
    stocks: list[str] = Field(..., min_length=2, description="NSE ticker symbols e.g. ['TCS.NS', 'INFY.NS']")
    start: str = Field(default="2020-01-01", description="Start date (YYYY-MM-DD)")
    end: str = Field(
        default_factory=lambda: (date.today() - timedelta(days=1)).isoformat(),
        description="End date (YYYY-MM-DD) — defaults to yesterday",
    )
    max_weight: float = Field(default=0.30, ge=0.10, le=0.50, description="Max allocation per stock (0.10–0.50)")

    @field_validator("start", "end")
    @classmethod
    def valid_date_format(cls, v: str) -> str:
        try:
            d = date.fromisoformat(v)
        except ValueError as exc:
            raise ValueError(f"Invalid date '{v}'. Expected YYYY-MM-DD.") from exc
        if d > date.today():
            raise ValueError(f"Date '{v}' cannot be in the future.")
        return v

    @model_validator(mode="after")
    def date_range_sensible(self) -> OptimizeRequest:
        start_d = date.fromisoformat(self.start)
        end_d = date.fromisoformat(self.end)
        if start_d >= end_d:
            raise ValueError("start must be before end.")
        if (end_d - start_d).days < 365:
            raise ValueError("Date range must be at least 1 year for reliable optimization.")
        return self

    @field_validator("stocks")
    @classmethod
    def at_least_two_unique(cls, v: list[str]) -> list[str]:
        unique = list(dict.fromkeys(v))  # deduplicate preserving order
        if len(unique) < 2:
            raise ValueError("At least 2 unique stocks are required.")
        return unique


class OptimizeResponse(BaseModel):
    portfolio_id: int
    expected_return: float
    volatility: float
    sharpe: float
    basket_return: float
    nifty_return: float
    alpha: float
    weights: dict[str, float]
    stocks_in_basket: int
    stocks_with_weight: int


class PortfolioListItem(BaseModel):
    id: int
    created_at: str
    tickers: list[str]
    start_date: str
    end_date: str
    expected_return: float
    volatility: float
    sharpe: float
    basket_return: float | None
    nifty_return: float | None
    max_weight: float
    num_portfolios: int


class PortfolioDetail(PortfolioListItem):
    weights: dict[str, float]


class DeleteResponse(BaseModel):
    message: str
    portfolio_id: int
