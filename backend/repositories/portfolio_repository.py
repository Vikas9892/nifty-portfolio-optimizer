import json

from src import database as db
from backend.schemas.portfolio import PortfolioDetail, PortfolioListItem


class PortfolioRepository:
    """Thin adapter between the SQLite layer and Pydantic schemas."""

    def save(
        self, tickers, start_date, end_date,
        expected_return, volatility, sharpe,
        basket_return, nifty_return,
        max_weight, num_portfolios, weights,
    ) -> int:
        return db.save_portfolio(
            tickers=tickers, start_date=start_date, end_date=end_date,
            expected_return=expected_return, volatility=volatility, sharpe=sharpe,
            basket_return=basket_return, nifty_return=nifty_return,
            max_weight=max_weight, num_portfolios=num_portfolios,
            weights=weights,
        )

    def get_all(self) -> list[PortfolioListItem]:
        history_df = db.load_portfolio_history()
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

    def get_by_id(self, portfolio_id: int) -> PortfolioDetail | None:
        row = db.load_portfolio_by_id(portfolio_id)
        if row is None:
            return None
        weights = db.load_portfolio_weights(portfolio_id)
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

    def delete(self, portfolio_id: int) -> bool:
        return db.delete_portfolio(portfolio_id)
