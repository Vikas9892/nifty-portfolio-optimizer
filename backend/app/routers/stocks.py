from config import NIFTY_50, NIFTY_50_STOCKS
from fastapi import APIRouter, Depends

from backend.app.core.dependencies import get_current_user
from backend.app.schemas.auth import UserResponse
from backend.app.schemas.response import SuccessResponse
from backend.app.schemas.stocks import StockUniverseResponse
from backend.app.services.cache_service import cache

router = APIRouter(prefix="/api/v1/stocks", tags=["Stocks"])

_UNIVERSE_TTL = 3600  # stock universe changes at most once a day


@router.get(
    "/",
    response_model=SuccessResponse[StockUniverseResponse],
    summary="Get the full Nifty 50 universe",
    description="Returns all 50 tickers grouped by sector. Requires authentication.",
)
def get_stocks(
    _: UserResponse = Depends(get_current_user),
) -> SuccessResponse[StockUniverseResponse]:
    hit = cache.get("stocks:universe")
    if hit is not None:
        return SuccessResponse(message="Stock universe fetched.", data=StockUniverseResponse(**hit))

    data = StockUniverseResponse(
        sectors=NIFTY_50,
        all_stocks=NIFTY_50_STOCKS,
        total_count=len(NIFTY_50_STOCKS),
    )
    cache.set("stocks:universe", data.model_dump(), ttl=_UNIVERSE_TTL)
    return SuccessResponse(message="Stock universe fetched.", data=data)
