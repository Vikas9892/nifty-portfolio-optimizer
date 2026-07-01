from fastapi import HTTPException

from src.data_service import get_prices
from src.optimizer import optimize_portfolio
from src.benchmark import compare_with_nifty

from backend.repositories.portfolio_repository import PortfolioRepository
from backend.schemas.portfolio import (
    DeleteResponse,
    OptimizeRequest,
    OptimizeResponse,
    PortfolioDetail,
    PortfolioListItem,
)


class PortfolioService:
    def __init__(self) -> None:
        self._repo = PortfolioRepository()

    def optimize(self, req: OptimizeRequest) -> OptimizeResponse:
        try:
            data = get_prices(tickers=req.stocks, start=req.start, end=req.end)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Price fetch failed: {exc}") from exc

        if data.empty:
            raise HTTPException(
                status_code=422,
                detail="No price data returned. Verify ticker symbols and date range.",
            )
        if len(data.columns) < 2:
            raise HTTPException(
                status_code=422,
                detail=f"Only {len(data.columns)} ticker(s) had sufficient data — need at least 2.",
            )

        try:
            _, _, weights, ret, vol, sharpe = optimize_portfolio(data, max_weight=req.max_weight)
            basket_return, nifty_return = compare_with_nifty(
                data, weights, start=req.start, end=req.end
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Optimization failed: {exc}") from exc

        nonzero = {k: v for k, v in weights.items() if v > 0}

        portfolio_id = self._repo.save(
            tickers=list(data.columns),
            start_date=req.start,
            end_date=req.end,
            expected_return=ret,
            volatility=vol,
            sharpe=sharpe,
            basket_return=basket_return,
            nifty_return=nifty_return,
            max_weight=req.max_weight,
            num_portfolios=0,  # Monte Carlo is a UI concern; not run via the API
            weights=dict(weights),
        )

        return OptimizeResponse(
            portfolio_id=portfolio_id,
            expected_return=ret,
            volatility=vol,
            sharpe=sharpe,
            basket_return=basket_return,
            nifty_return=nifty_return,
            alpha=basket_return - nifty_return,
            weights=nonzero,
            stocks_in_basket=len(data.columns),
            stocks_with_weight=len(nonzero),
        )

    def get_history(self) -> list[PortfolioListItem]:
        return self._repo.get_all()

    def get_by_id(self, portfolio_id: int) -> PortfolioDetail:
        portfolio = self._repo.get_by_id(portfolio_id)
        if portfolio is None:
            raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found.")
        return portfolio

    def delete(self, portfolio_id: int) -> DeleteResponse:
        if not self._repo.delete(portfolio_id):
            raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found.")
        return DeleteResponse(message=f"Portfolio {portfolio_id} deleted.", portfolio_id=portfolio_id)
