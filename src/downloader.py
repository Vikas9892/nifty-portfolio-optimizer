from typing import Sequence

import pandas as pd
import yfinance as yf


def fetch_from_yahoo(tickers: Sequence[str], start: str, end: str) -> pd.DataFrame:
    """Download close prices from Yahoo Finance. Returns wide-format DataFrame."""
    raw = yf.download(list(tickers), start=start, end=end, progress=False)
    if raw.empty:
        return pd.DataFrame()

    close = raw["Close"]
    # Single-ticker download returns a Series — normalise to DataFrame
    if isinstance(close, pd.Series):
        close = close.to_frame(name=list(tickers)[0])

    return close.dropna(how="all")


def fetch_missing(tickers: Sequence[str], from_date: str, end: str) -> pd.DataFrame:
    """Convenience wrapper: fetch only an incremental date range."""
    return fetch_from_yahoo(tickers, start=from_date, end=end)
