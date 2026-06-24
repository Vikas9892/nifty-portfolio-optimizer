"""Download and inspect Nifty stock price data."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from pypfopt import EfficientFrontier, expected_returns, risk_models
import yfinance as yf


STOCKS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
]
PLOTS_DIR = Path("plots")


def download_prices(start: str = "2020-01-01", end: str = "2025-01-01"):
    """Download adjusted closing prices for the project basket."""
    raw = yf.download(STOCKS, start=start, end=end, progress=False)
    close_prices = raw["Close"].dropna(how="all")
    output_path = Path("data") / "nifty_close_prices.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    close_prices.to_csv(output_path)
    return close_prices


def calculate_returns(price_data):
    """Convert close prices into daily returns."""
    returns = price_data.pct_change().dropna()
    return returns


def optimize_portfolio(price_data):
    """Optimize the basket for maximum Sharpe ratio."""
    mu = expected_returns.mean_historical_return(price_data)
    covariance = risk_models.sample_cov(price_data)
    frontier = EfficientFrontier(mu, covariance)
    frontier.max_sharpe()
    cleaned_weights = frontier.clean_weights()
    performance = frontier.portfolio_performance(verbose=True)
    return mu, covariance, cleaned_weights, performance


def simulate_portfolios(price_data, num_portfolios: int = 10000):
    """Generate random portfolios for a Monte Carlo frontier."""
    mu = expected_returns.mean_historical_return(price_data)
    covariance = risk_models.sample_cov(price_data)
    portfolio_rows = []
    asset_count = len(mu)

    for _ in range(num_portfolios):
        weights = np.random.random(asset_count)
        weights /= np.sum(weights)

        portfolio_return = np.dot(weights, mu.values)
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(covariance.values, weights)))
        sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility else 0

        portfolio_rows.append(
            {
                "return": portfolio_return,
                "volatility": portfolio_volatility,
                "sharpe": sharpe_ratio,
            }
        )

    return pd.DataFrame(portfolio_rows)


def save_frontier_plot(portfolios):
    """Save a Monte Carlo efficient frontier scatter plot."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(
        portfolios["volatility"],
        portfolios["return"],
        c=portfolios["sharpe"],
        cmap="viridis",
        s=8,
        alpha=0.7,
    )
    plt.colorbar(scatter, label="Sharpe Ratio")
    plt.title("Nifty Portfolio Monte Carlo Frontier")
    plt.xlabel("Annual Volatility")
    plt.ylabel("Annual Return")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "efficient_frontier.png", dpi=200)
    plt.close()


def save_correlation_heatmap(returns):
    """Save a correlation heatmap for the stock basket."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 6))
    sns.heatmap(returns.corr(), annot=True, cmap="coolwarm", fmt=".2f", square=True)
    plt.title("Stock Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "correlation_heatmap.png", dpi=200)
    plt.close()


def compare_with_nifty(price_data, weights):
    """Compare the optimized basket against the Nifty 50 benchmark."""
    nifty_close = yf.download("^NSEI", start="2020-01-01", end="2025-01-01", progress=False)["Close"].squeeze().dropna()
    nifty_return = float(nifty_close.pct_change().dropna().mean() * 252)

    daily_returns = price_data.pct_change().dropna()
    weight_series = pd.Series(weights)
    basket_return = float((daily_returns @ weight_series).mean() * 252)
    return basket_return, nifty_return


if __name__ == "__main__":
    data = download_prices()
    print(data.head())
    returns = calculate_returns(data)
    print(returns.head())
    mu, covariance, cleaned_weights, performance = optimize_portfolio(data)
    print(mu)
    print(covariance)
    print(cleaned_weights)
    print(performance)
    frontier = simulate_portfolios(data)
    save_frontier_plot(frontier)
    save_correlation_heatmap(returns)
    basket_return, nifty_return = compare_with_nifty(data, cleaned_weights)
    print({"basket_return": basket_return, "nifty_return": nifty_return})
