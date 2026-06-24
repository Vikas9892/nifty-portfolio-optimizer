"""Download and inspect Nifty stock price data."""

from pathlib import Path

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


if __name__ == "__main__":
    data = download_prices()
    print(data.head())
    returns = calculate_returns(data)
    print(returns.head())
