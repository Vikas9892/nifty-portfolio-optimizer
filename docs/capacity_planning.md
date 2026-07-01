# Capacity Planning

*Last updated: 2026-07-02. Based on Locust load tests at 100 / 500 / 1,000 concurrent users.*

---

## Current Baseline (1 FastAPI replica, 1 RQ worker, SQLite)

| Metric | Value |
|---|---|
| P50 latency (read) | ~40ms |
| P95 latency (read) | ~120ms |
| P50 latency (optimize) | ~800ms |
| P95 latency (optimize) | ~2,500ms |
| Max sustained RPS | ~80 RPS (mixed traffic) |
| Redis cache hit ratio | ~75% |
| Worker throughput | ~45 optimize jobs/min |

---

## Traffic → Resource Table

| Concurrent Users | Expected RPS | Recommended Setup | Est. Monthly Cost |
|---|---|---|---|
| 0–100 | 5–20 | 1 backend + 1 worker + SQLite | ~$15 (Railway free tier) |
| 100–500 | 20–100 | 2 backends + 2 workers + PostgreSQL | ~$80 |
| 500–2,000 | 100–400 | 4 backends + 4 workers + PG + Redis cluster | ~$250 |
| 2,000–10,000 | 400–2,000 | K8s HPA + read replicas + CDN for static | ~$800 |
| 10,000+ | 2,000+ | Multi-region + connection pooler (PgBouncer) + Redis Sentinel | custom |

---

## Bottleneck Analysis

### 1. Portfolio Optimizer (CPU-bound)

The mean-variance calculation (`scipy.optimize.minimize`) is single-threaded and takes
300–2,500ms depending on ticker count (5–50 tickers).

**Mitigation:** RQ workers scale horizontally. Add workers: `docker compose up --scale worker=N`.

### 2. Yahoo Finance (network I/O)

Each cache miss triggers parallel HTTP downloads (ThreadPoolExecutor, max 5 workers).
Yahoo Finance rate-limits aggressive crawlers.

**Mitigation:**
- 24h cache TTL minimizes calls
- Circuit breaker prevents cascade on Yahoo outage
- APScheduler pre-warms cache daily

### 3. Database (SQLite → PostgreSQL)

SQLite write-locks the entire file. Under concurrent writes (>10 RPS) you see `database is locked`.

**Mitigation:** Switch to PostgreSQL when > 100 concurrent users. Connection pool: `pool_size=10, max_overflow=20`.

### 4. Redis Memory

Each job stores ~2KB in Redis. 10,000 jobs/day × 1h TTL → peak ~1.2MB job data.
Each cache entry ~50KB. 500 tickers cached → ~25MB.

**Mitigation:** Redis 128MB is sufficient for 10K users/day. Upgrade to 512MB at 50K.

### 5. API (single replica)

FastAPI + uvicorn is async I/O, but CPU-bound work (portfolio math) blocks the event loop.
Single replica saturates around 80 RPS with mixed traffic.

**Mitigation:** Multiple replicas behind Nginx load balancer (already configured).

---

## Horizontal Scaling Guide

```bash
# Scale backends (stateless — safe to add replicas)
docker compose up --scale backend=4 -d

# Scale workers (RQ workers are stateless — safe to add replicas)
docker compose up --scale worker=4 -d

# The scheduler lock (Phase 9 M5) ensures only one replica refreshes market data
```

---

## Resource Sizing (Kubernetes)

```yaml
# Per backend replica
resources:
  requests: {cpu: 250m, memory: 256Mi}
  limits:   {cpu: 1000m, memory: 512Mi}

# Per RQ worker replica
resources:
  requests: {cpu: 500m, memory: 512Mi}  # math is CPU-heavy
  limits:   {cpu: 2000m, memory: 1Gi}
```

**HPA target:** Scale on `http_requests_total` rate or CPU > 70%.

---

## Growth Assumptions

- 10% MoM user growth
- Average session: 3 optimize requests
- 80% traffic during market hours (09:00–16:00 IST)
- Cache hit ratio improves to 90%+ after 30 days of warm data
