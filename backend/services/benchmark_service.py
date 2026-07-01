from fastapi import HTTPException

from src.data_service import get_prices
from src.benchmark import compare_with_nifty

from backend.schemas.benchmark import BenchmarkRequest, BenchmarkResponse


class BenchmarkService:
    def compare(self, req: BenchmarkRequest) -> BenchmarkResponse:
        try:
            data = get_prices(tickers=req.stocks, start=req.start, end=req.end)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Price fetch failed: {exc}") from exc

        if data.empty:
            raise HTTPException(status_code=422, detail="No price data for the requested tickers.")

        try:
            basket_return, nifty_return = compare_with_nifty(
                data, req.weights, start=req.start, end=req.end
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Benchmark comparison failed: {exc}") from exc

        alpha = basket_return - nifty_return
        return BenchmarkResponse(
            basket_return=basket_return,
            nifty_return=nifty_return,
            alpha=alpha,
            outperforms=alpha > 0,
        )
