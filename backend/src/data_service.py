from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from . import database as db
from .downloader import fetch_from_yahoo

_MAX_WORKERS = 5


def get_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    db.create_tables()
    latest = db.latest_date(tickers)

    missing = [t for t, d in latest.items() if d is None]
    stale = [t for t, d in latest.items() if d is not None and d < end]

    t0 = time.perf_counter()
    total_downloaded = 0

    if missing:
        new_data = fetch_from_yahoo(missing, start=start, end=end)
        if not new_data.empty:
            db.save_prices(new_data)
            total_downloaded += len(new_data.columns)

    if stale:
        by_cutoff: dict[str, list[str]] = {}
        for t in stale:
            by_cutoff.setdefault(latest[t], []).append(t)

        def _fetch_group(cutoff: str, group: list[str]) -> pd.DataFrame | None:
            from_date = (pd.Timestamp(cutoff) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            if from_date > end:
                return None
            return fetch_from_yahoo(group, start=from_date, end=end)

        with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(by_cutoff))) as pool:
            futures = {
                pool.submit(_fetch_group, cutoff, group): (cutoff, group)
                for cutoff, group in by_cutoff.items()
            }
            for future in as_completed(futures):
                try:
                    incremental = future.result()
                    if incremental is not None and not incremental.empty:
                        db.save_prices(incremental)
                        total_downloaded += len(incremental.columns)
                except Exception as exc:
                    _, group = futures[future]
                    logging.getLogger("nifty").warning(
                        "DATA_SERVICE | failed to fetch group %s: %s", group, exc
                    )

    prices = db.load_prices(tickers, start=start, end=end)
    if prices.empty:
        return prices

    threshold = int(0.80 * len(prices))
    return prices.dropna(axis=1, thresh=threshold).ffill()
