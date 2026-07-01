from __future__ import annotations

from pydantic import BaseModel, Field


class OptimizeRequest(BaseModel):
    stocks: list[str] = Field(..., min_length=2, description="NSE ticker symbols e.g. ['TCS.NS', 'INFY.NS']")
    start: str = Field(default="2020-01-01", description="Start date (YYYY-MM-DD)")
    end: str = Field(default="2025-01-01", description="End date (YYYY-MM-DD)")
    max_weight: float = Field(default=0.30, ge=0.10, le=0.50, description="Max allocation per stock (0.10–0.50)")


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
    """Full portfolio including per-ticker weights."""
    weights: dict[str, float]


class DeleteResponse(BaseModel):
    message: str
    portfolio_id: int
