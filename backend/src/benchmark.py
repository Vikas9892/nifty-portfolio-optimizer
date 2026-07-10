import pandas as pd
import yfinance as yf


def compare_with_nifty(price_data, weights, start: str = "2020-01-01", end: str = "2025-01-01"):
    """Compare the optimized basket against the Nifty 50 benchmark."""
    nifty_close = yf.download("^NSEI", start=start, end=end, progress=False)["Close"].squeeze().dropna()
    nifty_return = float(nifty_close.pct_change().dropna().mean() * 252)
    daily_returns = price_data.pct_change().dropna()
    weight_series = pd.Series(weights)
    weight_series = weight_series[weight_series.index.isin(daily_returns.columns)]
    basket_return = float((daily_returns[weight_series.index] @ weight_series).mean() * 252)
    return basket_return, nifty_return
