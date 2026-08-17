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
from backend.app.services.cache_service import cache
from backend.app.utils.exceptions import ExternalServiceError, OptimizationError, ValidationError
from backend.app.utils.logger import logger
from backend.src.benchmark import compare_with_nifty
from backend.src.data_service import get_prices
from backend.src.optimizer import optimize_portfolio

_HISTORY_TTL = 120  # 2 min — invalidated on save / delete
_DETAIL_TTL = 300  # 5 min


class PortfolioService:
    def __init__(self) -> None:
        self._repo = PortfolioRepository()
        self._audit = AuditRepository()

    def optimize(self, req: OptimizeRequest, user: UserResponse) -> OptimizeResponse:
        logger.info(
            "OPTIMIZE_START | user_id=%s stocks=%d range=%s→%s",
            user.id,
            len(req.stocks),
            req.start,
            req.end,
        )

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
            basket_return, nifty_return = compare_with_nifty(
                data, weights, start=req.start, end=req.end
            )
        except Exception as exc:
            raise OptimizationError(f"Optimization failed: {exc}") from exc

        nonzero = {k: v for k, v in weights.items() if v > 0}

        portfolio_id = self._repo.save(
            user_id=user.id,
            tickers=list(data.columns),
            start_date=req.start,
            end_date=req.end,
            expected_return=ret,
            volatility=vol,
            sharpe=sharpe,
            basket_return=basket_return,
            nifty_return=nifty_return,
            max_weight=req.max_weight,
            num_portfolios=0,
            weights=dict(weights),
        )

        # Invalidate the user's history cache so the new entry shows up immediately
        cache.delete(f"portfolio:history:{user.id}")

        self._audit.log(user.id, "PORTFOLIO_CREATED", f"id={portfolio_id} sharpe={sharpe:.2f}")
        logger.info(
            "OPTIMIZE_DONE | user_id=%s portfolio_id=%s sharpe=%.2f",
            user.id,
            portfolio_id,
            sharpe,
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

    def get_history(self, user: UserResponse) -> list[PortfolioListItem]:
        cache_key = f"portfolio:history:{user.id}"
        hit = cache.get(cache_key)
        if hit is not None:
            logger.debug("CACHE_HIT | %s", cache_key)
            return [PortfolioListItem(**item) for item in hit]

        items = self._repo.get_all_for_user(user.id)
        cache.set(cache_key, [i.model_dump() for i in items], ttl=_HISTORY_TTL)
        return items

    def get_by_id(self, portfolio_id: int, user: UserResponse) -> PortfolioDetail:
        # Key is scoped to the owner. PortfolioDetail carries no user_id, so a
        # shared "portfolio:<id>" key could not be ownership-checked on a hit and
        # served other users' portfolios to anyone who guessed an id. Scoping the
        # key means a non-owner simply misses and falls through to the repository,
        # which raises AuthorizationError.
        cache_key = f"portfolio:{user.id}:{portfolio_id}"
        hit = cache.get(cache_key)
        if hit is not None:
            logger.debug("CACHE_HIT | %s", cache_key)
            return PortfolioDetail(**hit)

        detail = self._repo.get_by_id(portfolio_id, user.id)
        cache.set(cache_key, detail.model_dump(), ttl=_DETAIL_TTL)
        return detail

    def delete(self, portfolio_id: int, user: UserResponse) -> DeleteResponse:
        result = self._repo.delete(portfolio_id, user.id)
        cache.delete(f"portfolio:{user.id}:{portfolio_id}")
        cache.delete(f"portfolio:history:{user.id}")
        self._audit.log(user.id, "PORTFOLIO_DELETED", f"id={portfolio_id}")
        logger.info("PORTFOLIO_DELETED | user_id=%s portfolio_id=%s", user.id, portfolio_id)
        return result
