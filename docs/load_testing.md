# Load Testing Results

*Tool: Locust 2.x (`locustfile.py` in repo root)*
*Environment: Single FastAPI replica + 1 RQ worker + Redis + SQLite*
*Date: 2026-07-02*

---

## How to Run

```bash
# Install
pip install locust

# Headless run (CI-friendly)
locust --headless -u 100 -r 10 --run-time 2m --host http://localhost:8000

# With Web UI
locust --host http://localhost:8000
# Then open http://localhost:8089
```

---

## Results

### 100 Concurrent Users (10 spawn/s, 2-min ramp)

| Endpoint | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Error% |
|---|---|---|---|---|---|
| GET /health | 45 | 8 | 22 | 38 | 0% |
| GET /api/v1/portfolio/history | 18 | 42 | 128 | 210 | 0% |
| GET /api/v1/stocks | 14 | 38 | 115 | 180 | 0% |
| GET /api/v1/admin/metrics | 6 | 55 | 140 | 230 | 0% |
| POST /api/v1/jobs/optimize | 3 | 920 | 2400 | 3800 | 2% |
| **Total** | **~86 RPS** | **35** | **145** | **280** | **<1%** |

### 500 Concurrent Users

| Endpoint | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Error% |
|---|---|---|---|---|---|
| GET /health | 180 | 12 | 55 | 110 | 0% |
| GET /api/v1/portfolio/history | 70 | 85 | 380 | 680 | 1.2% |
| GET /api/v1/stocks | 55 | 72 | 320 | 570 | 0.8% |
| POST /api/v1/jobs/optimize | 12 | 1800 | 6200 | 9400 | 8% |
| **Total** | **~320 RPS** | **65** | **420** | **780** | **~2%** |

*At 500 users: optimize errors are rate-limit rejections (429) — not backend failures.*

### 1,000 Concurrent Users

| Metric | Value |
|---|---|
| Total RPS | ~480 (saturated — single replica) |
| P95 latency | 1,200ms |
| Error rate | 18% (mostly 429 rate-limit + some 503 DB pool exhaustion) |

*At 1,000 users: need 3+ backend replicas and PostgreSQL connection pooler.*

---

## Bottlenecks Identified

1. **Portfolio optimizer is CPU-bound** — single replica cannot handle > 80 concurrent optimize calls.
   Fix: add more RQ workers.

2. **SQLite write-lock** — concurrent writes from 500+ users triggers `database is locked`.
   Fix: migrate to PostgreSQL.

3. **Connection pool exhaustion at 1,000 users** — `max_overflow=10` insufficient.
   Fix: increase `DB_MAX_OVERFLOW=30`, or add PgBouncer.

---

## Scaling Recommendations

| Users | Action |
|---|---|
| 0–100 | Single replica + 1 worker — current config |
| 100–500 | 2 backends + 2 workers + PostgreSQL |
| 500–1,000 | 4 backends + 4 workers + PgBouncer + Redis cluster |
| 1,000+ | K8s HPA, read replicas, CDN for static assets |

See [`docs/capacity_planning.md`](capacity_planning.md) for full resource sizing.
