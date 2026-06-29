"""Nifty 50 portfolio optimizer — full universe, user-selectable basket."""

from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from pypfopt import EfficientFrontier, expected_returns, risk_models
import streamlit.runtime as streamlit_runtime
import yfinance as yf


# Full Nifty 50 universe grouped by sector
NIFTY_50 = {
    "IT": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS", "INDUSINDBK.NS"],
    "Financial Services": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS", "SBILIFE.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS"],
    "FMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS"],
    "Pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS"],
    "Auto": ["MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "EICHERMOT.NS", "M&M.NS"],
    "Metals & Mining": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS"],
    "Cement": ["ULTRACEMCO.NS", "SHREECEM.NS", "GRASIM.NS"],
    "Conglomerate / Infra": ["LT.NS", "ADANIPORTS.NS", "ADANIENT.NS"],
    "Telecom": ["BHARTIARTL.NS"],
    "Consumer": ["ASIANPAINT.NS", "TITAN.NS"],
    "Healthcare": ["APOLLOHOSP.NS"],
    "Agro / Chemicals": ["UPL.NS"],
}

# Flatten to a single list for convenience
NIFTY_50_STOCKS: list[str] = [ticker for tickers in NIFTY_50.values() for ticker in tickers]

# Curated cross-sector default basket (good starting point for new users)
DEFAULT_STOCKS = [
    "TCS.NS", "INFY.NS", "HCLTECH.NS",          # IT
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS",    # Banking
    "RELIANCE.NS", "ONGC.NS",                    # Energy
    "HINDUNILVR.NS", "ITC.NS",                   # FMCG
    "SUNPHARMA.NS",                              # Pharma
    "MARUTI.NS", "TATAMOTORS.NS",                # Auto
    "BHARTIARTL.NS",                             # Telecom
    "LT.NS",                                     # Infra
]

PLOTS_DIR = Path("plots")


def download_prices(stocks: Sequence[str], start: str = "2020-01-01", end: str = "2025-01-01"):
    """Download adjusted closing prices for the given basket."""
    raw = yf.download(list(stocks), start=start, end=end, progress=False)
    close_prices = raw["Close"].dropna(how="all")
    # Drop stocks with too many missing values (less than 80% data coverage)
    threshold = int(0.80 * len(close_prices))
    close_prices = close_prices.dropna(axis=1, thresh=threshold).ffill()
    output_path = Path("data") / "nifty_close_prices.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    close_prices.to_csv(output_path)
    return close_prices


def calculate_returns(price_data):
    """Convert close prices into daily returns."""
    return price_data.pct_change().dropna()


def optimize_portfolio(price_data, max_weight: float = 0.30):
    """Optimize the basket for maximum Sharpe ratio using Ledoit-Wolf covariance."""
    mu = expected_returns.mean_historical_return(price_data)
    # Ledoit-Wolf shrinkage stabilizes the covariance matrix for larger asset sets
    covariance = risk_models.CovarianceShrinkage(price_data).ledoit_wolf()
    frontier = EfficientFrontier(mu, covariance)
    frontier.add_constraint(lambda w: w <= max_weight)
    frontier.max_sharpe()
    ret, vol, sharpe = frontier.portfolio_performance()
    cleaned_weights = frontier.clean_weights()
    return mu, covariance, cleaned_weights, ret, vol, sharpe


def simulate_portfolios(returns, num_portfolios: int = 5000):
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
        portfolio_rows.append({
            "return": portfolio_return,
            "volatility": portfolio_volatility,
            "sharpe": sharpe_ratio,
        })

    return pd.DataFrame(portfolio_rows)


def create_frontier_figure(portfolios, opt_ret: float, opt_vol: float):
    """Build a Monte Carlo efficient frontier figure."""
    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(
        portfolios["volatility"], portfolios["return"],
        c=portfolios["sharpe"], cmap="viridis", s=8, alpha=0.55,
    )
    ax.scatter([opt_vol], [opt_ret], marker="*", s=280, color="red", label="Optimized Portfolio")
    fig.colorbar(scatter, ax=ax, label="Sharpe Ratio")
    ax.set_title("Efficient Frontier (Monte Carlo)")
    ax.set_xlabel("Annual Volatility")
    ax.set_ylabel("Annual Return")
    ax.legend(loc="best")
    fig.subplots_adjust(top=0.90, right=0.88)
    return fig


def create_correlation_figure(returns):
    """Build a correlation heatmap figure."""
    corr = returns.corr()
    n = len(corr)
    fig_size = max(8, n * 0.55)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size * 0.75))
    sns.heatmap(
        corr, annot=(n <= 15), cmap="coolwarm", fmt=".2f",
        square=True, ax=ax, linewidths=0.3 if n <= 20 else 0,
    )
    ax.set_title("Correlation Heatmap")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


def create_dashboard_overview_figure(returns, portfolios, cleaned_weights, ret, vol, sharpe, nifty_return):
    """Build a static overview figure for README screenshots."""
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
    metrics_ax.text(0.01, 0.65, "Nifty Portfolio Optimizer Dashboard Overview",
                    fontsize=16, fontweight="bold", va="center")
    metrics_ax.text(0.01, 0.25, metrics_text, fontsize=12, va="center")

    frontier_ax = fig.add_subplot(grid[1, 0])
    scatter = frontier_ax.scatter(
        portfolios["volatility"], portfolios["return"],
        c=portfolios["sharpe"], cmap="viridis", s=7, alpha=0.5,
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
        values, labels=None, startangle=90,
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
    weight_series = weight_series[weight_series.index.isin(daily_returns.columns)]
    basket_return = float((daily_returns[weight_series.index] @ weight_series).mean() * 252)
    return basket_return, nifty_return


def plot_allocation_pie(weights):
    """Create a donut-style allocation chart."""
    non_zero_weights = {k: v for k, v in weights.items() if v > 0}
    labels = list(non_zero_weights.keys())
    values = list(non_zero_weights.values())

    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, _ = ax.pie(
        values, labels=None, startangle=90,
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
    data, returns, cleaned_weights, frontier,
    basket_return, nifty_return, ret, vol, sharpe,
    max_weight, num_portfolios,
):
    """Render the Streamlit dashboard."""
    import streamlit as st

    st.set_page_config(page_title="Nifty Portfolio Optimizer", layout="wide")
    st.title("Nifty Portfolio Optimizer")
    st.caption("Mean-variance optimization over the Nifty 50 universe with Ledoit-Wolf covariance shrinkage.")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Expected Return", f"{ret * 100:.2f}%")
    col2.metric("Volatility", f"{vol * 100:.2f}%")
    col3.metric("Sharpe Ratio", f"{sharpe:.2f}")
    col4.metric("Nifty 50 Return", f"{nifty_return * 100:.2f}%")
    col5.metric("vs Benchmark", f"{(basket_return - nifty_return) * 100:+.2f}%")

    st.subheader("Portfolio Summary")
    st.markdown(
        f"""
Stocks in basket: **{len(data.columns)}**
Stocks with non-zero weight: **{sum(1 for v in cleaned_weights.values() if v > 0)}**
Simulation count: **{num_portfolios:,}**
Max weight cap: **{max_weight * 100:.0f}%**
Covariance model: **Ledoit-Wolf Shrinkage**
Optimization method: **Maximum Sharpe Ratio**
"""
    )
    st.caption(f"Realized annualized basket return: {basket_return:.2%}")

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Optimal Weights")
        weights_frame = pd.DataFrame(list(cleaned_weights.items()), columns=["Ticker", "Weight"])
        weights_frame = weights_frame[weights_frame["Weight"] > 0].sort_values("Weight", ascending=False)
        weights_frame["Weight"] = weights_frame["Weight"].map(lambda x: f"{x:.2%}")
        st.dataframe(weights_frame, use_container_width=True)
    with right:
        st.subheader("Portfolio Allocation")
        st.pyplot(plot_allocation_pie(cleaned_weights), clear_figure=True)

    st.subheader("Correlation Heatmap")
    st.pyplot(create_correlation_figure(returns), clear_figure=True)

    st.subheader("Efficient Frontier")
    st.pyplot(create_frontier_figure(frontier, ret, vol), clear_figure=True)

    st.subheader("Daily Returns Snapshot")
    st.dataframe(returns.head(15), use_container_width=True)


def get_streamlit_inputs():
    """Collect interactive dashboard controls."""
    import streamlit as st

    st.sidebar.header("Controls")

    # Sector-grouped stock picker
    st.sidebar.subheader("Stock Universe")
    selected_stocks = []
    with st.sidebar.expander("Pick stocks by sector", expanded=False):
        for sector, tickers in NIFTY_50.items():
            defaults_in_sector = [t for t in tickers if t in DEFAULT_STOCKS]
            chosen = st.multiselect(sector, tickers, default=defaults_in_sector, key=f"sector_{sector}")
            selected_stocks.extend(chosen)

    # Also show a flat multiselect as a quick override
    st.sidebar.subheader("Or pick from full list")
    flat_selected = st.sidebar.multiselect(
        "All Nifty 50 stocks",
        NIFTY_50_STOCKS,
        default=[],
        help="Selections here are added on top of sector picks above.",
    )
    selected_stocks = list(dict.fromkeys(selected_stocks + flat_selected))  # deduplicate, preserve order

    if not selected_stocks:
        selected_stocks = DEFAULT_STOCKS

    st.sidebar.markdown("---")
    start_date = st.sidebar.date_input("Start date", value=pd.Timestamp("2020-01-01"))
    end_date = st.sidebar.date_input("End date", value=pd.Timestamp("2025-01-01"))
    max_weight = st.sidebar.slider("Max weight per stock", min_value=0.10, max_value=0.50, value=0.30, step=0.01)
    num_portfolios = st.sidebar.slider("Monte Carlo portfolios", min_value=1000, max_value=10000, value=5000, step=500)

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


def main():
    if running_in_streamlit():
        stocks, start, end, max_weight, num_portfolios = get_streamlit_inputs()
    else:
        stocks, start, end, max_weight, num_portfolios = DEFAULT_STOCKS, "2020-01-01", "2025-01-01", 0.30, 5000

    data, returns, cleaned_weights, frontier, basket_return, nifty_return, ret, vol, sharpe = run_pipeline(
        stocks=stocks, start=start, end=end, max_weight=max_weight, num_portfolios=num_portfolios,
    )

    if running_in_streamlit():
        render_dashboard(
            data=data, returns=returns, cleaned_weights=cleaned_weights, frontier=frontier,
            basket_return=basket_return, nifty_return=nifty_return,
            ret=ret, vol=vol, sharpe=sharpe, max_weight=max_weight, num_portfolios=num_portfolios,
        )


if __name__ == "__main__":
    main()
