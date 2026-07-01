from pydantic import BaseModel


class StockUniverseResponse(BaseModel):
    sectors: dict[str, list[str]]
    all_stocks: list[str]
    total_count: int
