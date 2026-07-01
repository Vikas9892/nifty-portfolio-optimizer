from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator


class BenchmarkRequest(BaseModel):
    stocks: list[str] = Field(..., min_length=1)
    weights: dict[str, float]
    start: str = "2020-01-01"
    end: str = "2025-01-01"

    @field_validator("start", "end")
    @classmethod
    def valid_date(cls, v: str) -> str:
        try:
            d = date.fromisoformat(v)
        except ValueError as exc:
            raise ValueError(f"Invalid date '{v}'. Expected YYYY-MM-DD.") from exc
        if d > date.today():
            raise ValueError(f"Date '{v}' cannot be in the future.")
        return v

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> BenchmarkRequest:
        total = sum(self.weights.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0 (got {total:.4f}).")
        return self


class BenchmarkResponse(BaseModel):
    basket_return: float
    nifty_return: float
    alpha: float
    outperforms: bool
