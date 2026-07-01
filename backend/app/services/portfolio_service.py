from src.data_service import get_prices
from src.optimizer import optimize_portfolio
from src.benchmark import compare_with_nifty

from backend.app.repositories.audit_repository import AuditRepository
from backend.app.repositories.portfolio_repository import PortfolioRepository
from backend.app.schemas.auth import UserResponse
from backend.app.schemas.portfolio import (
    DeleteResponse,
    OptimizeRequest,
    OptimizeResponse,
    PortfolioDetail,
    PortfolioListItem,
)
from backend.app.utils.exceptions import ExternalServiceError, OptimizationError, ValidationError
from backend.app.utils.logger import logger


class PortfolioService:
    def __init__(self) -> None:
        self._repo = PortfolioRepository()
        self._audit = AuditRepository()

    def optimize(self, req: OptimizeRequest, user: UserResponse) -> OptimizeResponse:
        logger.info("OPTIMIZE_START | user_id=%s stocks=%d range=%s→%s",
                    user.id, len(req.stocks), req.start, req.end)

        try:
            data = get_prices(tickers=req.stocks, start=req.start, end=req.end)
        except Exception as exc:
            raise ExternalServiceError(f"Price fetch failed: {exc}") from exc

        if data.empty:
            raise ValidationError("No price data returned. Verify ticker symbols and date range.")
        if len(data.columns) < 2:
            raise ValidationError(
                f"Only {len(data.columns)} ticker(s) had sufficient data — need at least 2."
            )

        try:
            _, _, weights, ret, vol, sharpe = optimize_portfolio(data, max_weight=req.max_weight)
            basket_return, nifty_return = compare_with_nifty(data, weights, start=req.start, end=req.end)
        except Exception as exc:
            raise OptimizationError(f"Optimization failed: {exc}") from exc

        nonzero = {k: v for k, v in weights.items() if v > 0}

        portfolio_id = self._repo.save(
            user_id=user.id,
            tickers=list(data.columns),
            start_date=req.start, end_date=req.end,
            expected_return=ret, volatility=vol, sharpe=sharpe,
            basket_return=basket_return, nifty_return=nifty_return,
            max_weight=req.max_weight, num_portfolios=0,
            weights=dict(weights),
        )

        self._audit.log(user.id, "PORTFOLIO_CREATED", f"id={portfolio_id} sharpe={sharpe:.2f}")
        logger.info("OPTIMIZE_DONE | user_id=%s portfolio_id=%s sharpe=%.2f",
                    user.id, portfolio_id, sharpe)

        return OptimizeResponse(
            portfolio_id=portfolio_id,
            expected_return=ret, volatility=vol, sharpe=sharpe,
            basket_return=basket_return, nifty_return=nifty_return,
            alpha=basket_return - nifty_return,
            weights=nonzero,
            stocks_in_basket=len(data.columns),
            stocks_with_weight=len(nonzero),
        )

    def get_history(self, user: UserResponse) -> list[PortfolioListItem]:
        return self._repo.get_all_for_user(user.id)

    def get_by_id(self, portfolio_id: int, user: UserResponse) -> PortfolioDetail:
        return self._repo.get_by_id(portfolio_id, user.id)

    def delete(self, portfolio_id: int, user: UserResponse) -> DeleteResponse:
        result = self._repo.delete(portfolio_id, user.id)
        self._audit.log(user.id, "PORTFOLIO_DELETED", f"id={portfolio_id}")
        logger.info("PORTFOLIO_DELETED | user_id=%s portfolio_id=%s", user.id, portfolio_id)
        return result
