from __future__ import annotations

import pandas as pd

from . import database as db
from .downloader import fetch_from_yahoo


def get_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """
    Return close prices for the requested tickers and date range.

    Serves from the SQLite cache where possible and only hits Yahoo Finance
    for tickers that are entirely missing or have stale (incomplete) data.
    Cache misses are saved back to the DB so subsequent calls are instant.
    """
    db.create_tables()

    latest = db.latest_date(tickers)

    # Tickers with no rows at all in the DB
    missing = [t for t, d in latest.items() if d is None]
    # Tickers present but whose latest stored date is before the requested end
    stale = [t for t, d in latest.items() if d is not None and d < end]

    if missing:
        new_data = fetch_from_yahoo(missing, start=start, end=end)
        if not new_data.empty:
            db.save_prices(new_data)

    if stale:
        # Batch stale tickers by their latest stored date to minimise round-trips
        by_cutoff: dict[str, list[str]] = {}
        for t in stale:
            by_cutoff.setdefault(latest[t], []).append(t)

        for cutoff, group in by_cutoff.items():
            from_date = (pd.Timestamp(cutoff) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            if from_date <= end:
                incremental = fetch_from_yahoo(group, start=from_date, end=end)
                if not incremental.empty:
                    db.save_prices(incremental)

    prices = db.load_prices(tickers, start=start, end=end)

    if prices.empty:
        return prices

    # Apply the same 80% coverage threshold and forward-fill as the original downloader
    threshold = int(0.80 * len(prices))
    return prices.dropna(axis=1, thresh=threshold).ffill()
