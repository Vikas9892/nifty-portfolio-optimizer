# ADR 006 — Why Background Jobs (Async Job System)

**Date:** 2026-07-02
**Status:** Accepted

## Problem

Portfolio optimization involves:
1. Downloading 5+ years of stock price data from Yahoo Finance (~2–15 seconds)
2. Computing Ledoit-Wolf covariance and running the Markowitz optimizer (~0.5–2 seconds)

If these run synchronously inside an HTTP request:
- The HTTP worker thread is blocked for up to 17 seconds
- Under load (100 concurrent users), all threads are saturated
- Client timeouts can interrupt work that's already completed
- Retrying a timed-out request runs the full job again (waste + inconsistency)

## Options Considered

| Approach | Unblocks HTTP | Resumable | Deduplication | Complexity |
|----------|--------------|-----------|---------------|-----------|
| Sync (current Phase 1–7) | ❌ | ❌ | ❌ | None |
| FastAPI BackgroundTasks | ✅ | ❌ | ❌ | Low |
| RQ (Redis Queue) worker | ✅ | ✅ | Via idempotency key | Low–Med |
| Celery + broker | ✅ | ✅ | ✅ | High |
| Dramatiq | ✅ | ✅ | ✅ | Medium |

## Decision

**RQ (Redis Queue) in production, FastAPI BackgroundTasks as dev fallback.**

The `_enqueue()` function in `routers/jobs.py` tries RQ first; if Redis is unavailable it falls back to `background_tasks.add_task()`. This means:

- **Development:** No worker process needed — optimization runs in-process after HTTP response
- **Production (Docker):** A dedicated `worker` container drains the `optimize` queue from Redis
- **Deduplication:** `Idempotency-Key` header stores a job_id in Redis for 1 hour — duplicate requests return the same job instead of rerunning

## Flow

```
POST /api/v1/jobs/optimize
        │
        ▼ (returns immediately — HTTP 202)
    job_id created in Redis
        │
        ▼
    RQ Worker picks up job
        │
        ├── mark_running
        ├── download prices (parallel via ThreadPoolExecutor)
        ├── run optimizer
        └── mark_completed / mark_failed

GET /api/v1/jobs/{job_id}  (frontend polls every 2s)
```

## Consequences

- **Positive:** HTTP threads are freed immediately — throughput scales with worker count, not job duration
- **Positive:** Failed jobs can be retried without re-queuing from the client
- **Positive:** Circuit breaker on Yahoo Finance + tenacity retry happen inside the worker — isolated from HTTP layer
- **Trade-off:** Polling adds 2–4 seconds of latency vs. synchronous response (acceptable UX trade-off for a computation this heavy)
