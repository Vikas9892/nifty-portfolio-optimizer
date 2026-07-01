# ADR 003 — Why Redis

**Date:** 2026-07-02
**Status:** Accepted

## Problem

We need a fast, shared store for:
1. **Cache:** Store Yahoo Finance price data and user portfolio lists to avoid redundant queries
2. **Job queue:** Phase 8 — async optimization jobs need a durable, distributed queue
3. **Metrics:** Atomic counters for cache hits, request counts, error rates
4. **Idempotency keys:** Prevent duplicate optimization jobs on retry

## Options Considered

| Store | Caching | Job queue | Atomic counters | Ops complexity |
|-------|---------|-----------|-----------------|----------------|
| Redis | ✅ | ✅ (RQ, Celery) | ✅ INCR/INCRBYFLOAT | Low (single binary) |
| Memcached | ✅ | ❌ | ❌ | Low |
| PostgreSQL | Partial | ✅ (pg queues) | ✅ | Already present |
| RabbitMQ | ❌ | ✅ (Celery) | ❌ | High |
| In-process dict | Dev only | ❌ | ❌ | None |

## Decision

**Redis.** Reasons:

1. **Unified store:** One service handles cache, job queue, counters, and pub/sub — fewer moving parts
2. **RQ compatibility:** The `rq` job queue runs natively on Redis with a single `Queue(connection=r)` call
3. **Atomic operations:** `INCR`, `INCRBYFLOAT`, `SETNX` give us race-free counters and idempotency
4. **Graceful degradation:** The app detects `REDIS_URL` at startup — if absent, all cache/queue operations become no-ops, so the app still works in development without Redis

## Consequences

- **Positive:** Cache TTL enforcement is built-in (`SETEX`) — no cleanup jobs needed
- **Positive:** Job status polling (`GET job:{id}`) is O(1)
- **Trade-off:** Redis is in-memory — job state is lost on Redis restart unless persistence (`--save`) is configured (it is, in docker-compose)
- **Future:** For multiple Redis nodes, switch to Redis Cluster mode (config only, no code changes)
