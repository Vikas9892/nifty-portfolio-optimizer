import streamlit.runtime as streamlit_runtime

from . import database as db
from .data_service import get_prices
from .returns import calculate_returns
from .optimizer import optimize_portfolio
from .simulator import simulate_portfolios
from .benchmark import compare_with_nifty
from .visualization import (
    create_frontier_figure,
    create_correlation_figure,
    plot_allocation_pie,
    create_dashboard_overview_figure,
    save_plot,
)


def running_in_streamlit():
    """Detect whether the script is running inside Streamlit."""
    return streamlit_runtime.exists()


def run_pipeline(stocks, start, end, max_weight, num_portfolios):
    """Fetch → optimize → simulate → benchmark → persist one full run."""
    data = get_prices(tickers=list(stocks), start=start, end=end)
    returns = calculate_returns(data)
    mu, covariance, cleaned_weights, ret, vol, sharpe = optimize_portfolio(data, max_weight=max_weight)
    frontier = simulate_portfolios(returns, num_portfolios=num_portfolios)
    basket_return, nifty_return = compare_with_nifty(data, cleaned_weights, start=start, end=end)

    db.save_portfolio(
        tickers=list(data.columns),
        start_date=start, end_date=end,
        expected_return=ret, volatility=vol, sharpe=sharpe,
        basket_return=basket_return, nifty_return=nifty_return,
        max_weight=max_weight, num_portfolios=num_portfolios,
        weights=dict(cleaned_weights),
    )

    save_plot(create_frontier_figure(frontier, ret, vol), "efficient_frontier.png")
    save_plot(create_correlation_figure(returns), "correlation_heatmap.png")
    save_plot(plot_allocation_pie(cleaned_weights), "portfolio_allocation.png")
    save_plot(
        create_dashboard_overview_figure(
            returns=returns, portfolios=frontier, cleaned_weights=cleaned_weights,
            ret=ret, vol=vol, sharpe=sharpe, nifty_return=nifty_return,
        ),
        "dashboard_overview.png",
    )

    print(f"Stocks in basket:  {list(data.columns)}")
    print(f"Cleaned weights:   {dict((k, v) for k, v in cleaned_weights.items() if v > 0)}")
    print(f"Return: {ret:.4f}  Volatility: {vol:.4f}  Sharpe: {sharpe:.4f}")
    print(f"Basket return: {basket_return:.4f}  Nifty return: {nifty_return:.4f}")

    return data, returns, cleaned_weights, frontier, basket_return, nifty_return, ret, vol, sharpe
