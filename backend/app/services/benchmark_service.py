from src.data_service import get_prices
from src.benchmark import compare_with_nifty

from backend.app.schemas.benchmark import BenchmarkRequest, BenchmarkResponse
from backend.app.utils.exceptions import ExternalServiceError, OptimizationError, ValidationError


class BenchmarkService:
    def compare(self, req: BenchmarkRequest) -> BenchmarkResponse:
        try:
            data = get_prices(tickers=req.stocks, start=req.start, end=req.end)
        except Exception as exc:
            raise ExternalServiceError(f"Price fetch failed: {exc}") from exc

        if data.empty:
            raise ValidationError("No price data for the requested tickers.")

        try:
            basket_return, nifty_return = compare_with_nifty(
                data, req.weights, start=req.start, end=req.end
            )
        except Exception as exc:
            raise OptimizationError(f"Benchmark comparison failed: {exc}") from exc

        alpha = basket_return - nifty_return
        return BenchmarkResponse(
            basket_return=basket_return,
            nifty_return=nifty_return,
            alpha=alpha,
            outperforms=alpha > 0,
        )
