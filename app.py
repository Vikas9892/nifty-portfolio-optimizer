"""Download and inspect Nifty stock price data."""

from pathlib import Path

from pypfopt import EfficientFrontier, expected_returns, risk_models
import yfinance as yf


STOCKS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
]


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
    weights = frontier.max_sharpe()
    cleaned_weights = frontier.clean_weights()
    performance = frontier.portfolio_performance(verbose=True)
    return mu, covariance, cleaned_weights, performance


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
