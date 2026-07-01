# Reliability Report

*Generated: 2026-07-02 — covers Phase 8 + Phase 9 SRE layer.*

---

## 1. System Overview

Nifty Portfolio Optimizer is a mean-variance portfolio optimization service built on:

| Component | Role |
|---|---|
| FastAPI (Python) | REST API — portfolio calculation, auth, async jobs |
| PostgreSQL / SQLite | Persistent storage — users, portfolios, price history |
| Redis | Cache, job queue (RQ), rate limiting, feature flags, locks, DLQ |
| RQ Worker | Background portfolio optimization |
| APScheduler | Daily market data refresh at 13:30 UTC (weekdays) |
| Prometheus + Grafana | Observability and dashboards |
| Alertmanager | Alert routing to Email and Slack |

---

## 2. Failure Scenarios and Recovery

### 2.1 Redis Unavailable

**Impact:** Cache misses, feature flags use defaults, rate limiting relaxed, job queue falls back to BackgroundTasks, distributed lock trivially acquired (single-instance safe).

**Detection:** `RedisDown` Prometheus alert fires within 1 minute.

**Recovery:**
1. Redis automatically reconnects when it comes back.
2. Warm cache is lost — first requests after recovery hit the DB directly.
3. RQ jobs already in queue are preserved (Redis persistence `--save 60 1`).

**Fallback chain:**
```
cache.get() → None  →  DB query (automatic)
RQ enqueue → Error  →  FastAPI BackgroundTask (automatic)
Rate limit → Error  →  No rate limit applied (fail-open)
```

### 2.2 Database Unavailable

**Impact:** All write operations fail (login, register, save portfolio). Read-heavy paths partially served from Redis cache.

**Detection:** `/ready` probe returns 503; Kubernetes/Docker marks pod not-ready.

**Recovery:**
1. Fix DB connectivity.
2. `/ready` automatically returns 200 when DB accepts connections.
3. No data loss — in-flight HTTP requests return 500 (no partial writes due to explicit transactions).

### 2.3 Yahoo Finance Unavailable

**Impact:** Market data refresh and stale-ticker re-downloads fail. Existing cached/DB prices are served.

**Detection:** Circuit breaker logs `→ OPEN after N failures`; visible on `GET /api/v1/sre/circuit-breakers`.

**Recovery:**
- Tenacity retries 3× with exponential back-off (1–10s) on each call.
- After `fail_max=5` consecutive failures, circuit opens for 60s.
- After `reset_timeout=60s`, one probe attempt is made (HALF_OPEN).
- On success → CLOSED. On failure → OPEN again.

### 2.4 Worker Process Crash

**Impact:** New optimize jobs queue in Redis but are not processed.

**Detection:** `DeepQueue` Prometheus alert (queue depth > 100 for 5 min).

**Recovery:**
1. Restart: `docker compose restart worker`.
2. Queued jobs resume automatically — RQ is durable.

### 2.5 Multiple Replicas (Race Condition)

**Impact (without fix):** Two scheduler replicas both call Yahoo Finance at 13:30 UTC.

**Fix (Phase 9 M5):** `acquire_lock("market-refresh", ttl=600)` — only the first replica to acquire the Redis lock proceeds; others log "skipped".

---

## 3. Retry Policy

| Layer | Policy |
|---|---|
| Yahoo Finance HTTP | Tenacity — 3 attempts, exp back-off 1–10s |
| Circuit breaker | OPEN after 5 failures; HALF_OPEN after 60s |
| Job task | 3 attempts (`DLQ_MAX_RETRIES`); DLQ on final failure |
| DB connection | pool_pre_ping=True — dead connections auto-replaced |
| HTTP client timeouts | 30s (Yahoo Finance) |

---

## 4. Circuit Breaker Policy

State machine for `yahoo-finance` breaker (and any future external service):

```
CLOSED  →  OPEN       when failures ≥ fail_max (5)
OPEN    →  HALF_OPEN  after reset_timeout (60s)
HALF_OPEN → CLOSED    on successful probe call
HALF_OPEN → OPEN      on failed probe call
```

Current breaker states: `GET /api/v1/sre/circuit-breakers` (authenticated).

---

## 5. Cache Strategy

| Data | TTL | Invalidated by |
|---|---|---|
| Portfolio prices | 24h | Market refresh, explicit `cache.delete()` |
| Stocks universe | 24h | Market refresh |
| Job status | 1h | Status transitions |
| Feature flags | 24h | `PUT /api/v1/sre/feature-flags/{flag}` |
| Idempotency keys | 1h | Expires naturally |
| DLQ entries | 7 days | `DELETE /api/v1/sre/dlq/{id}` |

Cache-aside pattern: read → miss → DB query → populate cache → return.

---

## 6. Monitoring and Alerts

### Prometheus Metrics (auto-instrumented)

- `http_requests_total{method, status, path}` — request counts
- `http_request_duration_seconds` — latency histogram (p50/p95/p99)
- `process_cpu_seconds_total` — CPU usage
- Custom: `metrics:cache:hit_ratio`, `metrics:optimize:avg_ms`, `jobs:completed`, `jobs:failed`

### Alert Rules (`alertmanager/alerting_rules.yml`)

| Alert | Condition | Severity | Action |
|---|---|---|---|
| APIDown | Backend unreachable 1m | critical | Page oncall |
| HighErrorRate | 5xx rate > 5% for 2m | warning | Slack |
| SlowP95 | P95 > 2s for 5m | warning | Slack |
| RedisDown | Redis unreachable 1m | critical | Page oncall |
| DeepQueue | Queue depth > 100 for 5m | warning | Slack |
| HighCPU | CPU > 90% for 5m | warning | Slack |

### Dashboards

- Grafana at `:3001` — API latency, error rate, cache hit ratio, queue depth
- Admin panel at `/admin` — live metrics from `GET /api/v1/admin/metrics`
- SRE panel at `GET /api/v1/sre/*` — circuit breakers, feature flags, DLQ

---

## 7. Capacity Planning

See [`docs/capacity_planning.md`](capacity_planning.md).

---

## 8. Disaster Recovery

See [`docs/disaster_recovery.md`](disaster_recovery.md).

---

## 9. Security

See [`docs/security_audit.md`](security_audit.md).

---

## 10. SLOs (Target)

| Metric | Target |
|---|---|
| API availability | 99.9% / month (~43min downtime) |
| P95 response time | < 500ms (read), < 5s (optimize) |
| Error rate | < 0.1% over 5-minute window |
| Job success rate | > 99% (rest go to DLQ for inspection) |
| RTO | < 15 minutes |
| RPO | < 1 hour (last Redis snapshot + DB WAL) |
