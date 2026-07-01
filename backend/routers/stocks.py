from fastapi import APIRouter

from backend.schemas.stocks import StockUniverseResponse
from config import NIFTY_50, NIFTY_50_STOCKS

router = APIRouter()


@router.get(
    "/",
    response_model=StockUniverseResponse,
    summary="Get the full Nifty 50 universe",
    description="Returns all 50 tickers grouped by sector, plus a flat list for convenience.",
)
def get_stocks() -> StockUniverseResponse:
    return StockUniverseResponse(
        sectors=NIFTY_50,
        all_stocks=NIFTY_50_STOCKS,
        total_count=len(NIFTY_50_STOCKS),
    )
