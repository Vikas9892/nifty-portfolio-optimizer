#!/usr/bin/env python3
"""
Benchmark script for Nifty Portfolio Optimizer (Phase 10 — M5).

Measures:
  - Python startup / import time
  - SQLite init + CRUD operations
  - In-memory cache operations
  - Portfolio optimization (mock data)
  - Bcrypt hashing
  - JWT encode/decode

Usage:
    python scripts/benchmark.py
    python scripts/benchmark.py --json    # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Helpers ────────────────────────────────────────────────────────────────────


def bench(label: str, fn, n: int = 50) -> dict:
    """Run fn n times and return latency statistics (ms)."""
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    stats = {
        "label": label,
        "n": n,
        "p50_ms": round(statistics.median(times), 3),
        "p95_ms": round(sorted(times)[int(n * 0.95)], 3),
        "p99_ms": round(sorted(times)[int(n * 0.99)], 3),
        "min_ms": round(min(times), 3),
        "max_ms": round(max(times), 3),
        "mean_ms": round(statistics.mean(times), 3),
    }
    return stats


def print_table(results: list[dict]) -> None:
    header = f"{'Label':<45} {'P50':>8} {'P95':>8} {'P99':>8} {'Mean':>8} {'N':>5}"
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for r in results:
        print(
            f"{r['label']:<45} {r['p50_ms']:>7.2f}ms {r['p95_ms']:>7.2f}ms "
            f"{r['p99_ms']:>7.2f}ms {r['mean_ms']:>7.2f}ms {r['n']:>5}"
        )
    print(sep)


# ── Benchmark functions ────────────────────────────────────────────────────────


def bench_sqlite(tmp_dir: str) -> list[dict]:
    import sqlite3

    db_path = os.path.join(tmp_dir, "bench.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, password_hash TEXT)"
    )
    conn.execute(
        "CREATE TABLE portfolios (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, created_at TEXT)"
    )
    conn.commit()

    results = []

    # Single insert
    results.append(
        bench(
            "SQLite: INSERT user row",
            lambda: conn.execute(
                "INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                ("Test User", "u@example.com", "hash"),
            )
            or conn.commit(),
            n=200,
        )
    )

    # Select by PK
    conn.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)", ("A", "a@a.com", "h"))
    conn.commit()
    results.append(
        bench(
            "SQLite: SELECT by primary key",
            lambda: conn.execute("SELECT * FROM users WHERE id=1").fetchone(),
            n=500,
        )
    )

    # Select all (small table)
    results.append(
        bench(
            "SQLite: SELECT all users (small table)",
            lambda: conn.execute("SELECT * FROM users").fetchall(),
            n=500,
        )
    )

    conn.close()
    return results


def bench_bcrypt() -> list[dict]:
    import bcrypt

    pw = b"Test1234"
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pw, salt)

    results = []
    results.append(
        bench(
            "bcrypt: hash password (rounds=12)",
            lambda: bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12)),
            n=5,
        )
    )
    results.append(
        bench(
            "bcrypt: verify password (rounds=12)",
            lambda: bcrypt.checkpw(pw, hashed),
            n=10,
        )
    )
    return results


def bench_jwt() -> list[dict]:
    from jose import jwt as jose_jwt

    secret = "benchmark-secret-key-not-for-prod"
    payload = {"sub": "42", "type": "access", "exp": 9999999999}

    results = []
    results.append(
        bench(
            "JWT: encode access token",
            lambda: jose_jwt.encode(payload, secret, algorithm="HS256"),
            n=500,
        )
    )
    token = jose_jwt.encode(payload, secret, algorithm="HS256")
    results.append(
        bench(
            "JWT: decode + verify token",
            lambda: jose_jwt.decode(
                token, secret, algorithms=["HS256"], options={"verify_exp": False}
            ),
            n=500,
        )
    )
    return results


def bench_optimization() -> list[dict]:
    import numpy as np

    results = []

    # 10-stock portfolio (typical small case)
    def _optimize_10():
        from pypfopt import EfficientFrontier, expected_returns, risk_models

        np.random.seed(42)
        prices = np.cumprod(1 + np.random.randn(252, 10) * 0.01, axis=0)
        import pandas as pd

        df = pd.DataFrame(prices, columns=[f"S{i}" for i in range(10)])
        mu = expected_returns.mean_historical_return(df)
        sigma = risk_models.sample_cov(df)
        ef = EfficientFrontier(mu, sigma, weight_bounds=(0, 0.3))
        ef.max_sharpe()
        ef.clean_weights()

    results.append(bench("Portfolio optimization: 10 stocks (252 days)", _optimize_10, n=10))

    # 20-stock portfolio
    def _optimize_20():
        from pypfopt import EfficientFrontier, expected_returns, risk_models

        np.random.seed(42)
        prices = np.cumprod(1 + np.random.randn(252, 20) * 0.01, axis=0)
        import pandas as pd

        df = pd.DataFrame(prices, columns=[f"S{i}" for i in range(20)])
        mu = expected_returns.mean_historical_return(df)
        sigma = risk_models.sample_cov(df)
        ef = EfficientFrontier(mu, sigma, weight_bounds=(0, 0.3))
        ef.max_sharpe()
        ef.clean_weights()

    results.append(bench("Portfolio optimization: 20 stocks (252 days)", _optimize_20, n=10))

    return results


def bench_pydantic() -> list[dict]:
    from pydantic import BaseModel

    class OptimizeRequest(BaseModel):
        tickers: list[str]
        start: str
        end: str
        risk_free_rate: float = 0.05
        max_weight: float = 0.30

    data = {
        "tickers": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"],
        "start": "2023-01-01",
        "end": "2023-12-31",
    }

    results = []
    results.append(
        bench(
            "Pydantic v2: model_validate (5 fields)",
            lambda: OptimizeRequest.model_validate(data),
            n=1000,
        )
    )
    req = OptimizeRequest.model_validate(data)
    results.append(
        bench(
            "Pydantic v2: model_dump",
            lambda: req.model_dump(),
            n=1000,
        )
    )
    return results


def bench_json_serialization() -> list[dict]:
    import json as _json

    data = {
        "status": "completed",
        "sharpe": 1.847,
        "expected_return": 0.312,
        "volatility": 0.156,
        "weights": {f"STOCK_{i}.NS": round(1 / 10, 4) for i in range(10)},
        "frontier": [[0.1 + i * 0.01, 0.2 + i * 0.005] for i in range(50)],
    }
    s = _json.dumps(data)

    results = []
    results.append(bench("JSON: dumps (portfolio result)", lambda: _json.dumps(data), n=1000))
    results.append(bench("JSON: loads (portfolio result)", lambda: _json.loads(s), n=1000))
    return results


# ── Main ────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output JSON instead of table")
    args = parser.parse_args()

    all_results = []

    print("\nBenchmarking SQLite...")
    with tempfile.TemporaryDirectory() as tmp:
        all_results.extend(bench_sqlite(tmp))

    print("Benchmarking bcrypt...")
    all_results.extend(bench_bcrypt())

    print("Benchmarking JWT...")
    all_results.extend(bench_jwt())

    print("Benchmarking Pydantic...")
    all_results.extend(bench_pydantic())

    print("Benchmarking JSON serialization...")
    all_results.extend(bench_json_serialization())

    print("Benchmarking portfolio optimization (slowest — please wait)...")
    all_results.extend(bench_optimization())

    print("\n=== Nifty Portfolio Optimizer — Benchmark Results ===\n")
    if args.json:
        print(json.dumps(all_results, indent=2))
    else:
        print_table(all_results)
        print("\nAll times in milliseconds. n = number of iterations.")


if __name__ == "__main__":
    main()
