# Scalability Playbook

**Version:** Phase 8 · Last updated: 2026-07-02

## Current Capacity

| Resource | Limit | Notes |
|----------|-------|-------|
| FastAPI replicas | 2 | `docker-compose.prod.yml` — behind nginx |
| DB connections | 5 pool + 10 overflow per replica | SQLAlchemy `pool_size` |
| Redis connections | Unlimited (single node) | Redis 7 handles ~65k connections |
| RQ workers | 1 | Scales horizontally — just add containers |
| Optimization throughput | ~5 concurrent | CPU-bound; 1 worker = 1 job at a time |

## Identified Bottlenecks

### 1. Yahoo Finance Downloads
**Current:** Parallel ThreadPoolExecutor (5 workers) per job  
**Bottleneck:** Yahoo Finance rate-limits aggressive crawlers (~2 req/s per IP)  
**Mitigation:** Circuit breaker (5 failures → 60s cooldown) + tenacity retry (3 attempts, exp back-off)  
**Next step:** Cache aggressively. Most data is only stale by 1 day; a shared Redis key avoids redundant downloads across jobs.

### 2. Optimization CPU
**Current:** Single-threaded scipy optimizer runs in the RQ worker process  
**Bottleneck:** 1 worker = 1 job at a time; adding stocks adds quadratic covariance computation  
**Next step:** Scale workers horizontally — `docker compose up --scale worker=4`

### 3. PostgreSQL
**Current:** pool_size=5, max_overflow=10 per replica → 30 connections total at 2 replicas  
**Bottleneck:** Max PostgreSQL connections (default 100) is not a problem yet  
**Next step:** Add PgBouncer as a connection pooler between FastAPI and PostgreSQL to support 100+ replicas

### 4. Redis
**Current:** Single Redis 7 node with AOF + RDB persistence  
**Bottleneck:** Redis is single-threaded for write commands; pipeline batching (used in `cache_service.py`) reduces round-trips  
**Next step:** Redis Sentinel for HA; Redis Cluster (3 shards) when single-node memory exceeds 80%

## Horizontal Scaling Plan

```
Current:
  Nginx → FastAPI ×2 → Redis (single) → PostgreSQL

Phase 9 target:
  Nginx → FastAPI ×8  → Redis Sentinel (1 primary + 2 replicas)
                     → PgBouncer → PostgreSQL (primary + read replica)
  RQ workers ×8 (auto-scale on queue depth via KEDA)
```

Steps:
1. Deploy behind a load balancer (done — nginx in docker-compose.prod.yml)
2. Scale FastAPI: `docker compose up --scale backend=8` (stateless — trivial)
3. Scale workers: `docker compose up --scale worker=8` (stateless — trivial)
4. Add read replica for PostgreSQL: `DATABASE_URL_RO=postgresql://...` for history/detail queries
5. Switch Redis to Sentinel: update `REDIS_URL=redis+sentinel://...`

## Vertical Scaling Plan

| Component | When to scale up | Target |
|-----------|-----------------|--------|
| FastAPI   | CPU >70% sustained | More replicas first |
| Worker    | Queue depth >50 sustained | More worker replicas first |
| Redis     | Memory >80% of available | Increase instance RAM |
| PostgreSQL| IOPS saturation | Move to SSD; increase `shared_buffers` |

## Failure Injection Testing (Milestone 19)

Run these scenarios quarterly to verify resilience:

| Scenario | How to inject | Expected behavior |
|----------|--------------|-------------------|
| PostgreSQL unavailable | `docker stop postgres` | `/ready` returns 503; new requests fail gracefully with 500 |
| Redis unavailable | `docker stop redis` | App runs without cache; jobs fall back to BackgroundTasks |
| Yahoo Finance timeout | `iptables -A OUTPUT -d finance.yahoo.com -j DROP` | Circuit breaker opens after 5 failures; returns 502 with clear message |
| Worker crash | `docker kill worker` | Jobs stay in `queued` state; restart worker to drain queue |
| Full disk | `dd if=/dev/zero of=/tmp/fill bs=1M` | PostgreSQL write fails; app returns 500 with DB error |

## Future Improvements

- **KEDA auto-scaling:** Scale worker replicas on Redis queue depth metric
- **S3/MinIO:** Move generated PDF reports out of DB into object storage (Milestone 14)
- **WebSocket push:** Replace polling with WS `notifications` channel — eliminate 2s poll latency (Milestone 15)
- **API versioning:** `/api/v2/` for breaking changes; deprecation notice in v1 headers (Milestone 16)
- **Read replicas:** Route `GET /api/v1/portfolio/history` to PostgreSQL read replica — zero write contention
- **CDN:** Front the frontend's static assets with Cloudflare — eliminates bandwidth cost for JS/CSS
