from pydantic import BaseModel


class BenchmarkRequest(BaseModel):
    stocks: list[str]
    weights: dict[str, float]
    start: str = "2020-01-01"
    end: str = "2025-01-01"


class BenchmarkResponse(BaseModel):
    basket_return: float
    nifty_return: float
    alpha: float
    outperforms: bool
