# Disaster Recovery Plan

*RTO (Recovery Time Objective): < 15 minutes.*
*RPO (Recovery Point Objective): < 1 hour.*

---

## Scope

This document covers recovery from:
1. Database corruption / accidental deletion
2. Redis data loss
3. Full service outage (host failure)
4. Bad deployment (regression)

---

## 1. Database Recovery

### PostgreSQL

**Backup strategy:**
- Continuous WAL archiving to S3 (Railway Postgres / Supabase)
- Daily `pg_dump` via cron: `scripts/backup_db.sh`
- Backups retained for 30 days

**Restore procedure:**
```bash
# From latest daily dump
psql $DATABASE_URL < backups/portfolio_$(date +%Y-%m-%d).sql

# From point-in-time (WAL) — if using managed Postgres with PITR
# Use provider console to restore to any point in the last 7 days
```

**Verify:**
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM portfolios;"
curl http://localhost:8000/ready
```

### SQLite (development)

```bash
# Restore from backup
cp data/portfolio.db.bak data/portfolio.db

# Or re-initialize (dev only — data loss)
python -c "from backend.app.models.database import init_all_tables; init_all_tables()"
```

**RPO for SQLite:** Last manual backup (not suitable for production).

---

## 2. Redis Recovery

Redis data (cache, job queue, DLQ, feature flags) is **ephemeral-first** — the system
is designed to work without Redis. Loss of Redis means:

- Cache is cold → higher DB load for ~24h
- Queued jobs are lost → users must resubmit optimize requests
- Feature flags reset to code defaults
- DLQ entries are lost (job IDs are logged — can manually re-investigate)

**Restore procedure:**
```bash
# Restart Redis (persistence enabled: --save 60 1)
docker compose restart redis

# Redis will replay its RDB snapshot from /data/dump.rdb (up to 60s stale)
# Warm cache is lost but will rebuild over 24h via normal traffic
```

**For zero-RPO on queue:** Use Redis Sentinel or Redis Cluster with AOF persistence.

---

## 3. Full Service Outage

```bash
# 1. Pull latest image
docker compose pull

# 2. Restart all services
docker compose up -d --force-recreate

# 3. Verify
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/api/v1/admin/metrics -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected recovery time:** 3–5 minutes (Docker image pull + container start).

---

## 4. Bad Deployment Rollback

```bash
# Identify last good commit
git log --oneline -10

# Revert to last known good image tag (example: previous deploy)
git checkout <good-commit-sha>
docker compose up --build -d

# Or if using container registry
docker compose pull backend:previous-tag
docker compose up -d
```

**Expected recovery time:** 5–10 minutes.

---

## 5. Runbooks

### "Optimize endpoint returning 500"

1. Check: `docker compose logs backend --tail 100 | grep ERROR`
2. Check: `GET /api/v1/sre/circuit-breakers` — is Yahoo Finance circuit OPEN?
3. Check: `GET /api/v1/sre/dlq` — are jobs piling up?
4. If circuit OPEN: wait 60s for HALF_OPEN probe, or restart the backend
5. If DLQ depth > 0: inspect jobs, fix root cause, retry via `POST /api/v1/sre/dlq/{id}/retry`

### "Database is locked (SQLite)"

1. Switch to PostgreSQL: update `DATABASE_URL=postgresql://...` in `.env`
2. `docker compose restart backend worker`

### "Redis OOM"

1. `redis-cli INFO memory` — check `used_memory_human`
2. Flush stale keys: `redis-cli --scan --pattern "job:*" | xargs redis-cli del`
3. Upgrade Redis instance memory limit

---

## 6. Contact

| Role | Contact |
|---|---|
| Backend on-call | oncall@nifty-portfolio.io |
| Infra | ops@nifty-portfolio.io |
| Escalation | Pagerduty — nifty-portfolio team |
