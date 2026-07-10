import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DB_PATH = Path("data") / "portfolio.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def create_tables():
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS prices (
                ticker       TEXT NOT NULL,
                date         TEXT NOT NULL,
                close        REAL NOT NULL,
                last_updated TEXT NOT NULL,
                PRIMARY KEY (ticker, date)
            );

            CREATE TABLE IF NOT EXISTS portfolios (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at      TEXT NOT NULL,
                tickers         TEXT NOT NULL,
                start_date      TEXT NOT NULL,
                end_date        TEXT NOT NULL,
                expected_return REAL NOT NULL,
                volatility      REAL NOT NULL,
                sharpe          REAL NOT NULL,
                basket_return   REAL,
                nifty_return    REAL,
                max_weight      REAL NOT NULL,
                num_portfolios  INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolio_weights (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL REFERENCES portfolios(id),
                ticker       TEXT NOT NULL,
                weight       REAL NOT NULL
            );
        """)


def save_prices(df: pd.DataFrame):
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for ticker in df.columns:
        for date_idx, close in df[ticker].dropna().items():
            date_str = date_idx.strftime("%Y-%m-%d") if hasattr(date_idx, "strftime") else str(date_idx)
            rows.append((ticker, date_str, float(close), now))

    with _connect() as conn:
        conn.executemany(
            """INSERT INTO prices (ticker, date, close, last_updated)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(ticker, date) DO UPDATE SET
                   close=excluded.close, last_updated=excluded.last_updated""",
            rows,
        )


def load_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    placeholders = ",".join("?" * len(tickers))
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT ticker, date, close FROM prices "
            f"WHERE ticker IN ({placeholders}) AND date BETWEEN ? AND ? ORDER BY date",
            tickers + [start, end],
        ).fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["ticker", "date", "close"])
    df["date"] = pd.to_datetime(df["date"])
    return df.pivot(index="date", columns="ticker", values="close").rename_axis(None, axis=1)


def latest_date(tickers: list[str]) -> dict[str, str | None]:
    placeholders = ",".join("?" * len(tickers))
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT ticker, MAX(date) FROM prices WHERE ticker IN ({placeholders}) GROUP BY ticker",
            tickers,
        ).fetchall()
    result: dict[str, str | None] = {t: None for t in tickers}
    for ticker, date in rows:
        result[ticker] = date
    return result
