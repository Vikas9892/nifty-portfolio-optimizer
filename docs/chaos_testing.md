# Chaos Testing Guide

*How we validate failure modes before they hit production.*

---

## Philosophy

Every failure scenario in `docs/reliability.md` should be **tested before prod**.
Chaos testing injects real failures and verifies the system degrades gracefully —
not silently or catastrophically.

---

## Prerequisites

```bash
# All services must be running
docker compose up -d

# Confirm health
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

---

## Scenarios

### 1. Kill Redis

**Expected:** Cache misses; jobs fall back to BackgroundTasks; feature flags use defaults.

```bash
# Inject
docker compose stop redis

# Verify degraded mode (should still return 200, just slower)
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/jobs/optimize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tickers":["RELIANCE.NS"],"start":"2024-01-01","end":"2024-12-31"}'

# Watch logs
docker compose logs backend --tail 50

# Recover
docker compose start redis
```

**Pass criteria:**
- `/health` returns 200
- `/ready` returns 200 (Redis is not a readiness dependency)
- Optimize endpoint returns 202 (job enqueued via BackgroundTask)
- No 500 errors in logs

---

### 2. Kill PostgreSQL / SQLite

**Expected:** `/ready` returns 503; read/write endpoints return 503 or 500.

```bash
# Inject (rename DB file)
mv data/portfolio.db data/portfolio.db.bak

# Verify
curl http://localhost:8000/ready   # should return 503
curl http://localhost:8000/health  # should still return 200 (liveness ≠ readiness)

# Recover
mv data/portfolio.db.bak data/portfolio.db
```

**Pass criteria:**
- `/health` returns 200 (process is alive)
- `/ready` returns 503 (DB unreachable)
- API endpoints that hit DB return appropriate error, not a stack trace

---

### 3. Kill Worker

**Expected:** Jobs queue in Redis but are not processed until worker restarts.

```bash
# Inject
docker compose stop worker

# Submit job
curl -X POST http://localhost:8000/api/v1/jobs/optimize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tickers":["TCS.NS"],"start":"2024-01-01","end":"2024-12-31"}'
# Save the job_id from response

# Poll — status should stay "queued"
curl http://localhost:8000/api/v1/jobs/$JOB_ID -H "Authorization: Bearer $TOKEN"

# Recover
docker compose start worker

# Poll again — job should transition to "completed" within 30s
curl http://localhost:8000/api/v1/jobs/$JOB_ID -H "Authorization: Bearer $TOKEN"
```

**Pass criteria:**
- Job remains `queued` while worker is down
- Job completes after worker restarts
- No data loss

---

### 4. Saturate the Queue

**Expected:** `DeepQueue` Prometheus alert fires; optimizer still accepts new jobs (no data loss).

```bash
# Submit 150 jobs rapidly (requires jq + a valid token)
for i in $(seq 1 150); do
  curl -s -X POST http://localhost:8000/api/v1/jobs/optimize \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"tickers":["INFY.NS"],"start":"2024-01-01","end":"2024-06-30"}' &
done
wait

# Check queue depth via admin metrics
curl http://localhost:8000/api/v1/admin/metrics -H "Authorization: Bearer $TOKEN"
```

**Pass criteria:**
- All 150 requests return 202
- `queue:depth` metric rises in Grafana
- After queue drains, all jobs are `completed` or `dead` (DLQ)

---

### 5. Trigger Circuit Breaker

**Expected:** After 5 Yahoo Finance failures, circuit opens; subsequent calls are rejected fast.

```bash
# Temporarily point Yahoo Finance to a bad URL (edit .env or env var)
export YAHOO_TIMEOUT_SECONDS=0.001  # force timeout

# Submit optimize with a fresh ticker (cache miss → Yahoo call)
for i in $(seq 1 6); do
  curl -X POST http://localhost:8000/api/v1/jobs/optimize \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"tickers":["WIPRO.NS"],"start":"2024-01-01","end":"2024-12-31"}'
done

# Check circuit state
curl http://localhost:8000/api/v1/sre/circuit-breakers -H "Authorization: Bearer $TOKEN"
# Should show "state": "open"
```

**Pass criteria:**
- Circuit transitions CLOSED → OPEN after 5 failures
- Subsequent calls return immediately with "circuit OPEN" error (no wait)
- State visible at `/api/v1/sre/circuit-breakers`

---

### 6. Duplicate Scheduler (Multi-Replica Race)

**Expected:** Only one replica refreshes market data; others log "skipped".

```bash
# Start 2 backend replicas
docker compose up --scale backend=2 -d

# Watch logs at 13:30 UTC (or trigger manually)
docker compose logs backend --follow | grep "market_refresh\|LOCK"
```

**Pass criteria:**
- One replica logs `SCHEDULER | market_refresh done`
- Other replica logs `SCHEDULER | skipped — another replica holds the market-refresh lock`
- No duplicate Yahoo Finance API calls

---

## scripts/chaos_test.sh

See `scripts/chaos_test.sh` for automated smoke-test versions of scenarios 1–3.

---

## Post-Chaos Verification

After each scenario, verify with:

```bash
# Full health check
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/api/v1/admin/metrics -H "Authorization: Bearer $TOKEN"

# DLQ is empty (no silent data loss)
curl http://localhost:8000/api/v1/sre/dlq -H "Authorization: Bearer $TOKEN"
```
