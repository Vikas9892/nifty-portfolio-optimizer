import streamlit.runtime as streamlit_runtime

from .downloader import download_prices
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
    """Execute data download, optimization, simulation, and benchmarking."""
    data = download_prices(stocks=stocks, start=start, end=end)
    returns = calculate_returns(data)
    mu, covariance, cleaned_weights, ret, vol, sharpe = optimize_portfolio(data, max_weight=max_weight)
    frontier = simulate_portfolios(returns, num_portfolios=num_portfolios)
    basket_return, nifty_return = compare_with_nifty(data, cleaned_weights, start=start, end=end)

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

    print(f"Stocks downloaded: {list(data.columns)}")
    print(f"Cleaned weights: {dict((k, v) for k, v in cleaned_weights.items() if v > 0)}")
    print(f"Return: {ret:.4f}  Volatility: {vol:.4f}  Sharpe: {sharpe:.4f}")
    print(f"Basket return: {basket_return:.4f}  Nifty return: {nifty_return:.4f}")

    return data, returns, cleaned_weights, frontier, basket_return, nifty_return, ret, vol, sharpe
