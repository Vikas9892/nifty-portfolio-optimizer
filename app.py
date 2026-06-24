"""Download and inspect Nifty stock price data."""

from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from pypfopt import EfficientFrontier, expected_returns, risk_models
import streamlit.runtime as streamlit_runtime
import yfinance as yf


STOCKS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
]
PLOTS_DIR = Path("plots")


def download_prices(stocks: Sequence[str], start: str = "2020-01-01", end: str = "2025-01-01"):
    """Download adjusted closing prices for the project basket."""
    raw = yf.download(list(stocks), start=start, end=end, progress=False)
    close_prices = raw["Close"].dropna(how="all")
    output_path = Path("data") / "nifty_close_prices.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    close_prices.to_csv(output_path)
    return close_prices


def calculate_returns(price_data):
    """Convert close prices into daily returns."""
    return price_data.pct_change().dropna()


def optimize_portfolio(price_data, max_weight: float = 0.30):
    """Optimize the basket for maximum Sharpe ratio under constraints."""
    mu = expected_returns.mean_historical_return(price_data)
    covariance = risk_models.sample_cov(price_data)
    frontier = EfficientFrontier(mu, covariance)
    frontier.add_constraint(lambda w: w <= max_weight)
    frontier.max_sharpe()
    ret, vol, sharpe = frontier.portfolio_performance()
    cleaned_weights = frontier.clean_weights()
    return mu, covariance, cleaned_weights, ret, vol, sharpe


def simulate_portfolios(returns, num_portfolios: int = 10000):
    """Generate random portfolios for a Monte Carlo frontier."""
    mean_returns = returns.mean()
    cov_matrix = returns.cov()
    portfolio_rows = []
    asset_count = len(mean_returns)

    for _ in range(num_portfolios):
        weights = np.random.random(asset_count)
        weights /= np.sum(weights)

        portfolio_return = np.sum(mean_returns.values * weights) * 252
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix.values * 252, weights)))
        sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility else 0

        portfolio_rows.append(
            {
                "return": portfolio_return,
                "volatility": portfolio_volatility,
                "sharpe": sharpe_ratio,
            }
        )

    return pd.DataFrame(portfolio_rows)


def create_frontier_figure(portfolios, opt_ret: float, opt_vol: float):
    """Build a Monte Carlo efficient frontier figure."""
    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(
        portfolios["volatility"],
        portfolios["return"],
        c=portfolios["sharpe"],
        cmap="viridis",
        s=8,
        alpha=0.55,
    )
    ax.scatter([opt_vol], [opt_ret], marker="*", s=280, color="red", label="Optimized Portfolio")
    fig.colorbar(scatter, ax=ax, label="Sharpe Ratio")
    ax.set_title("Efficient Frontier (Monte Carlo)")
    ax.set_xlabel("Annual Volatility")
    ax.set_ylabel("Annual Return")
    ax.legend(loc="best")
    fig.subplots_adjust(top=0.90, right=0.88, hspace=0.30, wspace=0.25)
    return fig


def create_correlation_figure(returns):
    """Build a correlation heatmap figure for the stock basket."""
    corr = returns.corr()
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", square=True, ax=ax)
    ax.set_title("Correlation Heatmap")
    fig.subplots_adjust(top=0.90, right=0.88, hspace=0.30, wspace=0.25)
    return fig


def create_dashboard_overview_figure(returns, portfolios, cleaned_weights, ret, vol, sharpe, nifty_return):
    """Build a static overview figure similar to the Streamlit dashboard."""
    fig = plt.figure(figsize=(14, 9))
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 3], hspace=0.28, wspace=0.22)

    metrics_ax = fig.add_subplot(grid[0, :])
    metrics_ax.axis("off")
    metrics_text = (
        f"Expected Return: {ret * 100:.2f}%    "
        f"Volatility: {vol * 100:.2f}%    "
        f"Sharpe Ratio: {sharpe:.2f}    "
        f"Nifty Return: {nifty_return * 100:.2f}%"
    )
    metrics_ax.text(
        0.01,
        0.65,
        "Nifty Portfolio Optimizer Dashboard Overview",
        fontsize=16,
        fontweight="bold",
        va="center",
    )
    metrics_ax.text(0.01, 0.25, metrics_text, fontsize=12, va="center")

    frontier_ax = fig.add_subplot(grid[1, 0])
    scatter = frontier_ax.scatter(
        portfolios["volatility"],
        portfolios["return"],
        c=portfolios["sharpe"],
        cmap="viridis",
        s=7,
        alpha=0.5,
    )
    frontier_ax.scatter([vol], [ret], marker="*", s=220, color="red")
    frontier_ax.set_title("Efficient Frontier")
    frontier_ax.set_xlabel("Annual Volatility")
    frontier_ax.set_ylabel("Annual Return")
    fig.colorbar(scatter, ax=frontier_ax, label="Sharpe Ratio")

    pie_ax = fig.add_subplot(grid[1, 1])
    non_zero_weights = {k: v for k, v in cleaned_weights.items() if v > 0}
    labels = list(non_zero_weights.keys())
    values = list(non_zero_weights.values())
    wedges, _ = pie_ax.pie(
        values,
        labels=None,
        startangle=90,
        explode=[0.03] * len(values),
        wedgeprops={"width": 0.45, "edgecolor": "white", "linewidth": 1.5},
    )
    legend_labels = [f"{ticker}: {weight:.1%}" for ticker, weight in zip(labels, values)]
    pie_ax.legend(wedges, legend_labels, title="Allocation", loc="center left", bbox_to_anchor=(1.0, 0.5))
    pie_ax.set_title("Portfolio Allocation")
    pie_ax.axis("equal")

    fig.subplots_adjust(top=0.90, right=0.88, hspace=0.30, wspace=0.25)
    return fig


def save_plot(fig, file_name: str):
    """Persist a matplotlib figure in the plots directory."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOTS_DIR / file_name, dpi=200)
    plt.close(fig)


def compare_with_nifty(price_data, weights, start: str = "2020-01-01", end: str = "2025-01-01"):
    """Compare the optimized basket against the Nifty 50 benchmark."""
    nifty_close = yf.download("^NSEI", start=start, end=end, progress=False)["Close"].squeeze().dropna()
    nifty_return = float(nifty_close.pct_change().dropna().mean() * 252)

    daily_returns = price_data.pct_change().dropna()
    weight_series = pd.Series(weights)
    basket_return = float((daily_returns @ weight_series).mean() * 252)
    return basket_return, nifty_return


def plot_allocation_pie(weights):
    """Create a clean donut-style allocation chart with separated wedges."""
    non_zero_weights = {k: v for k, v in weights.items() if v > 0}
    labels = list(non_zero_weights.keys())
    values = list(non_zero_weights.values())

    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, _ = ax.pie(
        values,
        labels=None,
        startangle=90,
        explode=[0.03] * len(values),
        wedgeprops={"width": 0.45, "edgecolor": "white", "linewidth": 1.5},
    )
    legend_labels = [f"{ticker}: {weight:.1%}" for ticker, weight in zip(labels, values)]
    ax.legend(wedges, legend_labels, title="Allocation", loc="center left", bbox_to_anchor=(1.0, 0.5))
    ax.set_title("Portfolio Allocation")
    ax.axis("equal")
    fig.tight_layout()
    return fig


def render_dashboard(
    data,
    returns,
    cleaned_weights,
    frontier,
    basket_return,
    nifty_return,
    ret,
    vol,
    sharpe,
    max_weight,
    num_portfolios,
):
    """Render the Streamlit dashboard."""
    import streamlit as st

    st.set_page_config(page_title="Nifty Portfolio Optimizer", layout="wide")
    st.title("Nifty Portfolio Optimizer")
    st.caption("A PyPortfolioOpt side project for stock selection, optimization, and benchmarking.")

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Expected Return", f"{ret * 100:.2f}%")
    metric_2.metric("Volatility", f"{vol * 100:.2f}%")
    metric_3.metric("Sharpe Ratio", f"{sharpe:.2f}")
    metric_4.metric("Nifty Return", f"{nifty_return * 100:.2f}%")

    st.subheader("Portfolio Summary")
    st.markdown(
        f"""
Stocks Selected: {len(data.columns)}  
Simulation Count: {num_portfolios}  
Max Weight Cap: {max_weight * 100:.0f}%  
Optimization Method: Maximum Sharpe Ratio
"""
    )

    st.caption(f"Optimized annualized basket return (realized): {basket_return:.2%}")

    st.subheader("Selected Stocks")
    st.write(list(data.columns))

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Optimal Weights")
        weights_frame = pd.DataFrame(list(cleaned_weights.items()), columns=["Ticker", "Weight"])
        weights_frame = weights_frame[weights_frame["Weight"] > 0]
        weights_frame["Weight"] = weights_frame["Weight"].map(lambda x: f"{x:.2%}")
        st.dataframe(weights_frame, width="stretch")
    with right:
        st.subheader("Portfolio Allocation Pie Chart")
        st.pyplot(plot_allocation_pie(cleaned_weights), clear_figure=True)

    st.subheader("Correlation Heatmap")
    st.pyplot(create_correlation_figure(returns), clear_figure=True)

    st.subheader("Efficient Frontier")
    st.pyplot(create_frontier_figure(frontier, ret, vol), clear_figure=True)

    st.subheader("Daily Returns Snapshot")
    st.dataframe(returns.head(15), width="stretch")


def get_streamlit_inputs():
    """Collect interactive dashboard controls."""
    import streamlit as st

    st.sidebar.header("Controls")
    selected_stocks = st.sidebar.multiselect("Select stocks", STOCKS, default=STOCKS)
    start_date = st.sidebar.date_input("Start date", value=pd.Timestamp("2020-01-01"))
    end_date = st.sidebar.date_input("End date", value=pd.Timestamp("2025-01-01"))
    max_weight = st.sidebar.slider("Max weight per stock", min_value=0.20, max_value=0.50, value=0.30, step=0.01)
    num_portfolios = st.sidebar.slider("Monte Carlo portfolios", min_value=2000, max_value=20000, value=10000, step=1000)

    if len(selected_stocks) < 2:
        st.error("Please select at least 2 stocks.")
        st.stop()

    if start_date >= end_date:
        st.error("Start date must be earlier than end date.")
        st.stop()

    return selected_stocks, str(start_date), str(end_date), max_weight, num_portfolios


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

    # Keep plot artifacts in the repository for README screenshots.
    save_plot(create_frontier_figure(frontier, ret, vol), "efficient_frontier.png")
    save_plot(create_correlation_figure(returns), "correlation_heatmap.png")
    save_plot(plot_allocation_pie(cleaned_weights), "portfolio_allocation.png")
    save_plot(
        create_dashboard_overview_figure(
            returns=returns,
            portfolios=frontier,
            cleaned_weights=cleaned_weights,
            ret=ret,
            vol=vol,
            sharpe=sharpe,
            nifty_return=nifty_return,
        ),
        "dashboard_overview.png",
    )

    print(data.head())
    print(returns.head())
    print(mu)
    print(covariance)
    print(cleaned_weights)
    print((ret, vol, sharpe))
    print({"basket_return": basket_return, "nifty_return": nifty_return})

    return data, returns, cleaned_weights, frontier, basket_return, nifty_return, ret, vol, sharpe


def main():
    if running_in_streamlit():
        stocks, start, end, max_weight, num_portfolios = get_streamlit_inputs()
    else:
        stocks, start, end, max_weight, num_portfolios = STOCKS, "2020-01-01", "2025-01-01", 0.30, 10000

    data, returns, cleaned_weights, frontier, basket_return, nifty_return, ret, vol, sharpe = run_pipeline(
        stocks=stocks,
        start=start,
        end=end,
        max_weight=max_weight,
        num_portfolios=num_portfolios,
    )

    if running_in_streamlit():
        render_dashboard(
            data=data,
            returns=returns,
            cleaned_weights=cleaned_weights,
            frontier=frontier,
            basket_return=basket_return,
            nifty_return=nifty_return,
            ret=ret,
            vol=vol,
            sharpe=sharpe,
            max_weight=max_weight,
            num_portfolios=num_portfolios,
        )


if __name__ == "__main__":
    main()
