import json

import src.database as _core_db
from backend.app.models import database as db
from backend.app.schemas.portfolio import DeleteResponse, PortfolioDetail, PortfolioListItem
from backend.app.utils.exceptions import AuthorizationError, NotFoundError


class PortfolioRepository:
    def save(self, user_id: int, tickers, start_date, end_date,
             expected_return, volatility, sharpe, basket_return, nifty_return,
             max_weight, num_portfolios, weights) -> int:
        return db.save_portfolio_for_user(
            user_id=user_id,
            tickers=tickers, start_date=start_date, end_date=end_date,
            expected_return=expected_return, volatility=volatility, sharpe=sharpe,
            basket_return=basket_return, nifty_return=nifty_return,
            max_weight=max_weight, num_portfolios=num_portfolios, weights=weights,
        )

    def get_all_for_user(self, user_id: int) -> list[PortfolioListItem]:
        history_df = db.load_portfolio_history_for_user(user_id)
        if history_df.empty:
            return []
        return [
            PortfolioListItem(
                id=int(row["id"]),
                created_at=row["created_at"],
                tickers=json.loads(row["tickers"]),
                start_date=row["start_date"],
                end_date=row["end_date"],
                expected_return=row["expected_return"],
                volatility=row["volatility"],
                sharpe=row["sharpe"],
                basket_return=row["basket_return"],
                nifty_return=row["nifty_return"],
                max_weight=row["max_weight"],
                num_portfolios=int(row["num_portfolios"]),
            )
            for _, row in history_df.iterrows()
        ]

    def get_by_id(self, portfolio_id: int, user_id: int) -> PortfolioDetail:
        row = _core_db.load_portfolio_by_id(portfolio_id)
        if not row:
            raise NotFoundError("Portfolio")
        owner = db.get_portfolio_owner(portfolio_id)
        # owner is None means the row exists but has no user_id (legacy/orphan).
        # Either way, only the owning user may access it.
        if owner != user_id:
            raise AuthorizationError("You don't own this portfolio.")
        weights = _core_db.load_portfolio_weights(portfolio_id)
        return PortfolioDetail(
            id=int(row["id"]),
            created_at=row["created_at"],
            tickers=json.loads(row["tickers"]),
            start_date=row["start_date"],
            end_date=row["end_date"],
            expected_return=row["expected_return"],
            volatility=row["volatility"],
            sharpe=row["sharpe"],
            basket_return=row["basket_return"],
            nifty_return=row["nifty_return"],
            max_weight=row["max_weight"],
            num_portfolios=int(row["num_portfolios"]),
            weights=weights,
        )

    def delete(self, portfolio_id: int, user_id: int) -> DeleteResponse:
        row = _core_db.load_portfolio_by_id(portfolio_id)
        if not row:
            raise NotFoundError("Portfolio")
        owner = db.get_portfolio_owner(portfolio_id)
        if owner != user_id:
            raise AuthorizationError("You don't own this portfolio.")
        _core_db.delete_portfolio(portfolio_id)
        return DeleteResponse(message=f"Portfolio {portfolio_id} deleted.", portfolio_id=portfolio_id)
