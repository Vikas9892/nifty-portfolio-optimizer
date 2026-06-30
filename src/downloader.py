from pathlib import Path
from typing import Sequence

import yfinance as yf


def download_prices(stocks: Sequence[str], start: str = "2020-01-01", end: str = "2025-01-01"):
    """Download adjusted closing prices for the given basket."""
    raw = yf.download(list(stocks), start=start, end=end, progress=False)
    close_prices = raw["Close"].dropna(how="all")
    threshold = int(0.80 * len(close_prices))
    close_prices = close_prices.dropna(axis=1, thresh=threshold).ffill()
    output_path = Path("data") / "nifty_close_prices.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    close_prices.to_csv(output_path)
    return close_prices
