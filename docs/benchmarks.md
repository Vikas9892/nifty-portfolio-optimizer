# Performance Benchmarks — Nifty Portfolio Optimizer

> Version: 4.0.0 · Last updated: 2026-07-02
> Machine: Windows 11, Python 3.11, in-process benchmarks (no network I/O)

Run the benchmarks yourself:
```bash
python scripts/benchmark.py
python scripts/benchmark.py --json    # machine-readable
```

---

## Results Summary

| Category | Operation | P50 | P95 | P99 | Mean |
|---|---|---|---|---|---|
| **Database** | SQLite INSERT user | 0.002ms | 0.003ms | 0.08ms | 0.009ms |
| **Database** | SQLite SELECT by PK | 0.037ms | 0.075ms | 0.12ms | 0.047ms |
| **Database** | SQLite SELECT all (small) | 0.201ms | 0.366ms | 0.526ms | 0.241ms |
| **Auth** | bcrypt hash (rounds=12) | 265.7ms | 269.7ms | 269.7ms | 266.1ms |
| **Auth** | bcrypt verify (rounds=12) | 268.0ms | 308.2ms | 308.2ms | 271.2ms |
| **Auth** | JWT encode (HS256) | 0.022ms | 0.041ms | 0.079ms | 0.049ms |
| **Auth** | JWT decode + verify | 0.042ms | 0.066ms | 0.205ms | 0.048ms |
| **Serialization** | Pydantic validate (5 fields) | 0.003ms | 0.003ms | 0.004ms | 0.003ms |
| **Serialization** | Pydantic model_dump | 0.003ms | 0.003ms | 0.005ms | 0.003ms |
| **Serialization** | JSON dumps (portfolio) | 0.071ms | 0.087ms | 0.138ms | 0.073ms |
| **Serialization** | JSON loads (portfolio) | 0.031ms | 0.050ms | 0.081ms | 0.034ms |
| **Optimizer** | PyPfOpt 10 stocks (252 days) | 19.8ms | — | — | 20–22ms |
| **Optimizer** | PyPfOpt 20 stocks (252 days) | 21.2ms | 31.7ms | 31.7ms | 22.3ms |

---

## Detailed Analysis

### Database Latency

```
SQLite INSERT (n=200)
───────────────────────────────────────────────────────────────
  P50:  0.002ms   P95: 0.003ms   P99: 0.08ms   Max: 1.3ms
  ▸ The spike to 1.3ms at P99+ is OS-level file flush.

SQLite SELECT by PK (n=500)
───────────────────────────────────────────────────────────────
  P50:  0.037ms   P95: 0.075ms   P99: 0.12ms   Max: 0.28ms
  ▸ Consistent; PK lookup is O(log n) via B-tree index.

SQLite SELECT all users — small table (n=500)
───────────────────────────────────────────────────────────────
  P50:  0.201ms   P95: 0.366ms   P99: 0.526ms  Max: 0.64ms
  ▸ 5× slower than PK lookup. In prod (PostgreSQL), this
    query would get a WHERE user_id=? and be equally fast.
```

**PostgreSQL in production**: Expect 0.3–2ms for indexed lookups over TCP (loopback), depending on connection pool state. Add 1–3ms for cross-container network.

---

### Authentication

```
bcrypt (rounds=12) — hashing (n=5)
───────────────────────────────────────────────────────────────
  P50: 265.7ms   P95: 269.7ms   Mean: 266.1ms

bcrypt (rounds=12) — verification (n=10)
───────────────────────────────────────────────────────────────
  P50: 268.0ms   P95: 308.2ms   Mean: 271.2ms
```

**Why this slowness is intentional**: Bcrypt with rounds=12 means an attacker can test ~3–4 passwords/second/CPU core. For an online brute force (where the attacker must call the API), this is irrelevant — rate limiting handles that. For offline attacks on a stolen hash database, 265ms per attempt provides meaningful resistance.

**Impact on API throughput**: Login is a low-frequency operation. A user logs in once per session. 265ms/login is imperceptible to users and has no impact on portfolio or market endpoints.

```
JWT HS256 encode (n=500)
───────────────────────────────────────────────────────────────
  P50: 0.022ms   P95: 0.041ms   Mean: 0.049ms

JWT HS256 decode + verify (n=500)
───────────────────────────────────────────────────────────────
  P50: 0.042ms   P95: 0.066ms   Mean: 0.048ms
```

**Auth overhead per request**: ~0.05ms for JWT decode. Negligible. With Python-jose (HMAC-SHA256), verification is CPU-cheap compared to bcrypt.

---

### Serialization

```
Pydantic v2 model_validate (n=1000)
───────────────────────────────────────────────────────────────
  P50: 0.003ms   P95: 0.003ms   P99: 0.004ms   Mean: 0.003ms

Pydantic v2 model_dump (n=1000)
───────────────────────────────────────────────────────────────
  P50: 0.003ms   P95: 0.003ms   P99: 0.005ms   Mean: 0.003ms
```

Pydantic v2's Rust core (`pydantic-core`) makes validation essentially free at this scale. Validating 1000 requests takes ~3ms total.

```
JSON dumps — portfolio result (n=1000)
───────────────────────────────────────────────────────────────
  Payload: { weights: {10 stocks}, frontier: 50 points }
  P50: 0.071ms   P95: 0.087ms   P99: 0.138ms   Mean: 0.073ms

JSON loads — portfolio result (n=1000)
───────────────────────────────────────────────────────────────
  P50: 0.031ms   P95: 0.050ms   P99: 0.081ms   Mean: 0.034ms
```

---

### Portfolio Optimization

```
10-stock portfolio, 252 trading days (n=10 runs, warm)
───────────────────────────────────────────────────────────────
  Warm P50: ~20ms   Mean: 20–22ms
  Cold start (first run, includes module imports): ~3100ms

20-stock portfolio, 252 trading days (n=10 runs)
───────────────────────────────────────────────────────────────
  P50: 21.2ms   P95: 31.7ms   Mean: 22.3ms
```

**Cold vs. warm**: The first optimization run includes Python module imports (NumPy, SciPy, PyPfOpt). Subsequent runs on a warm worker reuse the loaded modules and are consistently 18–32ms.

**Real-world timing** (with Yahoo Finance download):

| Operation | Time |
|---|---|
| Yahoo Finance download — 5 tickers, 1 year | 2,000–8,000ms |
| Yahoo Finance download — 20 tickers, 1 year | 5,000–15,000ms |
| PyPfOpt optimization (in-process) | 18–32ms |
| DB write (save result) | ~2ms |
| **Total end-to-end (warm, no cache)** | **~3–10 seconds** |
| **Total end-to-end (cache hit)** | **< 50ms** |

This is why the async worker pattern is essential. A 10s optimization running synchronously in the request handler would block all other requests for that Uvicorn worker.

---

## API Latency Budget

Target for non-optimization endpoints (portfolio list, job status, auth):

```
JWT decode:          0.05ms
DB query (PK):       0.05ms (SQLite) / 1ms (PostgreSQL)
Pydantic serialize:  0.07ms
Total serialization: ~1-2ms
                     ────────
FastAPI overhead:    ~1ms
Network (local):     ~0.5ms
                     ────────
Target P95:          < 50ms for GET /jobs/{id}
                     < 100ms for POST /portfolio/save
```

---

## Memory Usage

| Component | Baseline | Under load (50 concurrent) |
|---|---|---|
| FastAPI process (uvicorn) | ~80 MB | ~120 MB |
| RQ Worker (1 process) | ~150 MB | ~200 MB (NumPy loaded) |
| Redis | ~20 MB | ~50 MB (with cached data) |
| PostgreSQL | ~50 MB | ~80 MB |
| React SPA (browser) | ~45 MB | ~60 MB |
| Nginx | ~5 MB | ~10 MB |
| **Total stack** | **~350 MB** | **~520 MB** |

**Node**: On a 2GB RAM VPS, the full stack fits comfortably with room for the OS and PostgreSQL buffer pool.

---

## Throughput (Locust Load Test Results)

*See `docs/load_testing.md` for full Locust setup and scenarios.*

| Concurrency | RPS | P95 Latency | Error Rate |
|---|---|---|---|
| 10 users | 45 req/s | 28ms | 0% |
| 50 users | 180 req/s | 52ms | 0% |
| 100 users | 220 req/s | 98ms | < 0.1% |
| 500 users | 240 req/s | 430ms | 2.1% |
| 1000 users | 210 req/s | 890ms | 8.4% |

**Bottleneck at 500+**: PostgreSQL connection pool saturation (configured `max_size=10`). Increasing pool size or adding a connection pooler (PgBouncer) would lift this ceiling.

---

## Cache Effectiveness

When market data is cached (Redis TTL = 24h):

| Scenario | Latency |
|---|---|
| Portfolio optimize — Redis cache hit | < 50ms API response (job + cached prices) |
| Portfolio optimize — Redis cache miss | 3,000–15,000ms (includes Yahoo download) |
| Cache hit rate (typical market hours) | ~90% (data refreshed once per 15 min) |

**95th percentile optimization latency with cache**: ~25ms for the API call + job queuing. Worker finishes in ~25ms (cached prices + PyPfOpt). Total wall-clock: < 100ms.

---

## Benchmark ASCII Chart

```
Latency (ms, log scale)
1000ms │  ████████████ bcrypt (266ms)
 100ms │
  10ms │           ████ optimizer (20ms)
   1ms │
 0.1ms │  ███ JSON (0.07ms)
0.01ms │  █ JWT encode (0.022ms)
0.001ms│  █ Pydantic (0.003ms)

       └─────────────────────────────────────
         auth  serialize  optimize  query
```

---

## Profiling Notes

To profile a single optimization request end-to-end:

```bash
# Install py-spy
pip install py-spy

# Profile a running worker
py-spy top --pid $(pgrep -f "rq worker")

# Generate flamegraph
py-spy record -o profile.svg --pid $(pgrep -f "rq worker") -- python -c "
from backend.app.workers.tasks import portfolio_optimize_task
portfolio_optimize_task('test-job-id')
"
```

Typical hotspots:
1. `yfinance.download()` — 90% of wall time (network I/O)
2. `numpy.cov()` via `sample_cov()` — 5% of CPU time
3. `scipy.optimize.minimize()` inside EfficientFrontier — 3% of CPU time
4. DB writes — 2% of time
