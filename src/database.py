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
    """Upsert wide-format close prices (columns=tickers, index=dates) into the DB."""
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
    """Return a wide-format close-price DataFrame from the DB."""
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
    """Return the most recent stored date per ticker (None if absent)."""
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


def save_portfolio(
    tickers, start_date, end_date,
    expected_return, volatility, sharpe,
    basket_return, nifty_return,
    max_weight, num_portfolios,
    weights: dict,
) -> int:
    """Persist an optimization run and return its auto-generated ID."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO portfolios
               (created_at, tickers, start_date, end_date, expected_return, volatility, sharpe,
                basket_return, nifty_return, max_weight, num_portfolios)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (now, json.dumps(sorted(tickers)), start_date, end_date,
             expected_return, volatility, sharpe, basket_return, nifty_return,
             max_weight, num_portfolios),
        )
        portfolio_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO portfolio_weights (portfolio_id, ticker, weight) VALUES (?, ?, ?)",
            [(portfolio_id, t, w) for t, w in weights.items() if w > 0],
        )
    return portfolio_id


def load_portfolio_history() -> pd.DataFrame:
    """Return all past optimization runs ordered by most recent first."""
    with _connect() as conn:
        rows = conn.execute(
            """SELECT id, created_at, tickers, start_date, end_date,
                      expected_return, volatility, sharpe,
                      basket_return, nifty_return, max_weight, num_portfolios
               FROM portfolios ORDER BY created_at DESC"""
        ).fetchall()

    if not rows:
        return pd.DataFrame()

    cols = ["id", "created_at", "tickers", "start_date", "end_date",
            "expected_return", "volatility", "sharpe",
            "basket_return", "nifty_return", "max_weight", "num_portfolios"]
    return pd.DataFrame(rows, columns=cols)


def load_portfolio_weights(portfolio_id: int) -> dict[str, float]:
    """Return ticker→weight mapping for a given portfolio ID, sorted by weight."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ticker, weight FROM portfolio_weights WHERE portfolio_id = ? ORDER BY weight DESC",
            (portfolio_id,),
        ).fetchall()
    return dict(rows)


def load_portfolio_by_id(portfolio_id: int) -> dict | None:
    """Return a single portfolio row as a dict, or None if not found."""
    cols = ["id", "created_at", "tickers", "start_date", "end_date",
            "expected_return", "volatility", "sharpe",
            "basket_return", "nifty_return", "max_weight", "num_portfolios"]
    with _connect() as conn:
        row = conn.execute(
            f"SELECT {', '.join(cols)} FROM portfolios WHERE id = ?",
            (portfolio_id,),
        ).fetchone()
    return dict(zip(cols, row)) if row else None


def delete_portfolio(portfolio_id: int) -> bool:
    """Delete a portfolio and its weights. Returns True if the row existed."""
    with _connect() as conn:
        conn.execute("DELETE FROM portfolio_weights WHERE portfolio_id = ?", (portfolio_id,))
        cur = conn.execute("DELETE FROM portfolios WHERE id = ?", (portfolio_id,))
        return cur.rowcount > 0
