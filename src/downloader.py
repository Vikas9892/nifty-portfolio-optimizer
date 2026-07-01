"""Yahoo Finance download with exponential-backoff retry and circuit breaker."""
from __future__ import annotations

from typing import Sequence

import pandas as pd
import yfinance as yf
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

import logging
_log = logging.getLogger("nifty")


# ── Tenacity retry (wraps the raw yf.download call) ──────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    before_sleep=before_sleep_log(_log, logging.WARNING),
    reraise=True,
)
def _download_raw(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """Inner download — retried automatically on transient Yahoo Finance errors."""
    return yf.download(tickers, start=start, end=end, progress=False)


# ── Circuit breaker state (module-level singleton) ────────────────────────────

_cb_failures = 0
_cb_opened_at: float | None = None
_CB_FAIL_MAX = 5
_CB_RESET_TIMEOUT = 60  # seconds

def _circuit_open() -> bool:
    """Return True if the Yahoo Finance circuit breaker is currently OPEN."""
    import time
    global _cb_failures, _cb_opened_at
    if _cb_failures >= _CB_FAIL_MAX:
        if _cb_opened_at and (time.monotonic() - _cb_opened_at) > _CB_RESET_TIMEOUT:
            # HALF_OPEN: allow one probe through
            return False
        return True
    return False


def _record_success() -> None:
    global _cb_failures, _cb_opened_at
    _cb_failures = 0
    _cb_opened_at = None


def _record_failure() -> None:
    import time
    global _cb_failures, _cb_opened_at
    _cb_failures += 1
    if _cb_failures >= _CB_FAIL_MAX and _cb_opened_at is None:
        _cb_opened_at = time.monotonic()
        _log.error(
            "CIRCUIT[yahoo] | OPEN after %d failures — will retry in %ds",
            _cb_failures,
            _CB_RESET_TIMEOUT,
        )


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_from_yahoo(tickers: Sequence[str], start: str, end: str) -> pd.DataFrame:
    """
    Download close prices from Yahoo Finance.

    Resilience stack (outermost → innermost):
      1. Circuit breaker — fails fast when Yahoo is down (avoids thundering herd)
      2. Tenacity retry  — handles transient HTTP errors with exponential back-off
    """
    if _circuit_open():
        raise RuntimeError(
            "Yahoo Finance circuit breaker is OPEN — service temporarily unavailable."
        )

    try:
        raw = _download_raw(list(tickers), start=start, end=end)
        _record_success()
    except Exception as exc:
        _record_failure()
        raise exc

    if raw.empty:
        return pd.DataFrame()

    close = raw["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(name=list(tickers)[0])

    return close.dropna(how="all")


def fetch_missing(tickers: Sequence[str], from_date: str, end: str) -> pd.DataFrame:
    """Convenience wrapper: fetch only an incremental date range."""
    return fetch_from_yahoo(tickers, start=from_date, end=end)
