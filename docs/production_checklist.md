# Production Readiness Checklist — Nifty Portfolio Optimizer

> Version: 4.0.0 · Last updated: 2026-07-02

Use this checklist before every production deployment. Each item has a verification command.

---

## 1. HTTPS / TLS

- [ ] **TLS certificate installed** — Nginx serves `https://` on port 443.
  ```bash
  curl -I https://yourdomain.com/health
  # Expect: HTTP/2 200, strict-transport-security header
  ```

- [ ] **HTTP → HTTPS redirect** — Port 80 permanently redirects to 443.
  ```bash
  curl -I http://yourdomain.com/
  # Expect: 301 or 308 Location: https://...
  ```

- [ ] **TLS 1.2+ only** — TLS 1.0 and 1.1 disabled.
  ```bash
  nmap --script ssl-enum-ciphers -p 443 yourdomain.com
  # Expect: TLSv1.2 or TLSv1.3 only
  ```

- [ ] **Certificate expiry monitored** — Alert fires 30 days before expiry.
  ```bash
  echo | openssl s_client -connect yourdomain.com:443 2>/dev/null \
    | openssl x509 -noout -dates
  ```

- [ ] **HSTS header set** — `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  ```bash
  curl -I https://yourdomain.com/ | grep -i strict
  ```

---

## 2. Secrets Management

- [ ] **No secrets in `.env` files committed to git**
  ```bash
  git log --all --oneline -- .env
  # Should return nothing
  git grep -r "SECRET_KEY" -- "*.py" "*.yml" "*.json"
  # Expect: only references, not literal secret values
  ```

- [ ] **`SECRET_KEY` is a random 32-byte hex string** — Not the default `dev-secret-change-in-prod`.
  ```bash
  # Generate:
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

- [ ] **`DATABASE_URL` uses strong password** — Not `postgres:password`.
- [ ] **Redis has `requirepass` set** — Unauthenticated Redis access disabled.
  ```bash
  redis-cli -h redis-host ping
  # Expect: NOAUTH Authentication required.
  ```

- [ ] **Secrets injected via environment variables** — Not baked into Docker images.
  ```bash
  docker inspect api | jq '.[].Config.Env' | grep -v SECRET
  # No secrets in Docker inspect output
  ```

- [ ] **`.env.example` documents all required variables** — New deploys have a template.

---

## 3. Monitoring

- [ ] **Prometheus scrapes `/metrics`** — All metric families collecting.
  ```bash
  curl http://localhost:8000/metrics | grep "# HELP"
  # Expect: http_requests_total, http_request_duration_seconds, etc.
  ```

- [ ] **Grafana dashboard accessible** — Shows request rate, latency, error rate.
  ```bash
  curl -u admin:admin http://localhost:3001/api/health
  # Expect: {"database": "ok"}
  ```

- [ ] **Alertmanager running** — Alert routing configured for on-call.
  ```bash
  curl http://localhost:9093/api/v2/status | jq .status
  ```

- [ ] **All 6 alert rules loaded** — See `alertmanager/alerting_rules.yml`.
  ```bash
  curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules | length'
  # Expect: 6 rules
  ```

- [ ] **`HighErrorRate` alert fires in test** — Trigger 5xx errors, verify alert routes.

- [ ] **Dashboard shows last 24h data** — Prometheus retention is ≥ 15 days.
  ```bash
  # In prometheus.yml:
  # storage.tsdb.retention.time: 15d
  ```

---

## 4. Database Backup

- [ ] **Automated daily backup configured** — Cron job or cloud backup enabled.
  ```bash
  # PostgreSQL backup:
  pg_dump $DATABASE_URL | gzip > backup_$(date +%Y%m%d).sql.gz
  ```

- [ ] **Backup restoration tested** — Restore last backup to a staging environment.
  ```bash
  gunzip -c backup_latest.sql.gz | psql $STAGING_DATABASE_URL
  ```

- [ ] **Backup retention ≥ 7 days** — 7 daily backups stored.
- [ ] **Backup stored off-host** — Not on the same server (use S3, GCS, or backup service).
- [ ] **Point-in-time recovery configured** — PostgreSQL WAL archiving enabled for prod.
- [ ] **RTO and RPO defined** — See `docs/disaster_recovery.md`.

---

## 5. Health Checks

- [ ] **Liveness probe returns 200** — FastAPI `/health/live`.
  ```bash
  curl http://localhost:8000/health/live
  # Expect: {"status": "alive"}
  ```

- [ ] **Readiness probe returns 200** — FastAPI `/health/ready` (checks DB + Redis).
  ```bash
  curl http://localhost:8000/health/ready
  # Expect: {"status": "ready", "db": "ok", "redis": "ok"}
  ```

- [ ] **Liveness ≠ Readiness** — Liveness checks only that the process is alive. Readiness checks that it can serve traffic.
  - Liveness failure → container restart.
  - Readiness failure → remove from load balancer pool, do NOT restart.

- [ ] **Health checks configured in `docker-compose.yml`**:
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  ```

- [ ] **Nginx upstream health check** — Nginx only routes to healthy API instances.

---

## 6. Readiness (Staging Gate)

- [ ] **All tests pass on CI** — Zero failures, coverage ≥ 80%.
  ```bash
  python -m pytest --cov=backend/app --cov-fail-under=80
  ```

- [ ] **No linting errors**:
  ```bash
  python -m ruff check backend/app/
  python -m black --check backend/app/ backend/main.py
  ```

- [ ] **`docker compose up --build` starts without errors**:
  ```bash
  docker compose up --build -d
  docker compose ps
  # All services: State = Up
  ```

- [ ] **Smoke test passes** — `scripts/chaos_test.sh` runs end-to-end.
  ```bash
  bash scripts/chaos_test.sh
  ```

- [ ] **Migration applied** — DB schema matches code:
  ```bash
  alembic upgrade head
  ```

- [ ] **Feature flags defaulting correctly** — Verify in production env:
  ```bash
  curl -H "Authorization: Bearer $ADMIN_TOKEN" \
    http://localhost:8000/api/v1/sre/feature-flags/ENABLE_CACHE
  ```

---

## 7. Scaling

- [ ] **Worker count matches load** — 1 worker per 2 CPUs (CPU-bound optimization).
  ```bash
  docker compose up --scale worker=4 -d
  ```

- [ ] **Database connection pool sized correctly**:
  ```python
  # backend/app/db/database.py
  Database(url, min_size=2, max_size=10)
  # Rule: max_size ≤ (postgres max_connections / replicas)
  ```

- [ ] **Redis maxmemory policy set** — Prevents OOM on cache growth.
  ```bash
  redis-cli CONFIG SET maxmemory 512mb
  redis-cli CONFIG SET maxmemory-policy allkeys-lru
  ```

- [ ] **Nginx upstream load balancing** — Multiple API instances configured.
  ```nginx
  upstream api {
      server api1:8000;
      server api2:8000;
      server api3:8000;
      keepalive 32;
  }
  ```

- [ ] **Distributed lock prevents duplicate scheduler runs** — Test with 2 replicas:
  ```bash
  docker compose up --scale api=2 -d
  # Observe only one scheduler log line per 15-minute interval.
  ```

- [ ] **Circuit breaker thresholds tuned for prod load** — Review `failure_threshold=5, recovery_timeout=60`.

- [ ] **Resource limits set in docker-compose** — Prevent one container starving others:
  ```yaml
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '1.0'
  ```

---

## 8. Logging

- [ ] **JSON structured logging enabled in production** — `LOG_FORMAT=json` in prod env.
  ```bash
  # Verify:
  docker compose logs api | head -5
  # Expect: {"ts": "...", "level": "INFO", "msg": "...", "request_id": "..."}
  ```

- [ ] **All logs go to stdout** — Containers must not write to log files.
  ```bash
  docker compose logs --tail=100 api
  ```

- [ ] **Log aggregation configured** — Logs shipped to Loki/ELK/CloudWatch.
  ```yaml
  # docker-compose.yml
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
  ```

- [ ] **No secrets in logs** — Passwords, tokens never logged.
  ```bash
  docker compose logs api | grep -i "password\|secret\|token"
  # Should be empty or only redacted placeholders
  ```

- [ ] **Correlation IDs present on every request** — `X-Request-ID` in all log lines.
  ```bash
  curl -H "X-Request-ID: test-id-123" http://localhost:8000/health/live
  docker compose logs api | grep "test-id-123"
  # Should appear in the log entry
  ```

- [ ] **Log retention policy defined** — Old logs rotated after 30 days (see `max-file` config).

---

## 9. Disaster Recovery

*See `docs/disaster_recovery.md` for full runbook.*

- [ ] **RTO documented** — Recovery Time Objective: ≤ 1 hour for full stack.
- [ ] **RPO documented** — Recovery Point Objective: ≤ 24 hours (daily backups).

- [ ] **Runbook tested** — At least one full DR drill per quarter:
  1. Restore DB from latest backup.
  2. Bring up all services from Docker Compose.
  3. Verify `/health/ready` returns `{"status": "ready"}`.
  4. Test login, optimize, and portfolio save flows.

- [ ] **Backup encryption** — Backups encrypted at rest (AES-256).
- [ ] **Multi-region or off-site backup** — At least one backup copy off the primary server.

- [ ] **DLQ monitored** — Alert if DLQ depth > 10:
  ```bash
  # Prometheus alert: dlq_depth_high (see alerting_rules.yml)
  curl http://localhost:8000/api/v1/sre/dlq | jq length
  ```

---

## 10. Alerting

- [ ] **Alertmanager receives alerts from Prometheus** — Test alert pipeline:
  ```bash
  # Trigger a test alert:
  curl -X POST http://localhost:9093/api/v2/alerts \
    -H 'Content-Type: application/json' \
    -d '[{"labels": {"alertname": "TestAlert", "severity": "warning"}}]'
  # Verify: email/Slack/PagerDuty receives alert
  ```

- [ ] **All 6 alert rules confirmed**:
  - `HighErrorRate` — >5% 5xx for 5 minutes.
  - `SlowAPIResponse` — P95 latency > 2s for 10 minutes.
  - `WorkerQueueDepth` — Queue > 100 jobs for 15 minutes.
  - `CircuitBreakerOpen` — Any breaker in OPEN state for 5 minutes.
  - `HighMemoryUsage` — Memory > 80% for 10 minutes.
  - `DatabaseConnectionsHigh` — Postgres connections > 80% of max.

- [ ] **Receiver configuration tested**:
  - Email SMTP credentials work.
  - Slack webhook URL is valid and posts to correct channel.
  - PagerDuty integration key configured (for severity=critical).

- [ ] **Alert silencing works** — Can silence alerts during planned maintenance:
  ```bash
  # Via Alertmanager UI or API
  curl -X POST http://localhost:9093/api/v2/silences \
    -H 'Content-Type: application/json' \
    -d '{"matchers": [{"name": "alertname", "value": "HighMemoryUsage"}], ...}'
  ```

- [ ] **On-call rotation documented** — Who gets paged for which severity?
  - `warning` → Slack notification.
  - `critical` → PagerDuty page.

---

## Pre-Deployment Checklist (Run Every Deploy)

```bash
# 1. Tests
python -m pytest --cov=backend/app --cov-fail-under=80

# 2. Lint
python -m ruff check backend/app/
python -m black --check backend/app/ backend/main.py

# 3. Build
docker compose build --no-cache

# 4. Bring up
docker compose up -d

# 5. Health check
sleep 15
curl http://localhost:8000/health/ready

# 6. Smoke test
bash scripts/chaos_test.sh

# 7. Verify metrics
curl http://localhost:8000/metrics | grep -c "# HELP"
```

All steps must pass before traffic is routed to the new deployment.

---

## Security Checklist

- [ ] **CORS origins restricted** — Not `allow_origins=["*"]` in production.
  ```python
  # backend/app/core/config.py
  cors_origins: list[str] = ["https://yourdomain.com"]
  ```

- [ ] **Rate limiting configured** — Prevent brute-force on `/auth/login`.
- [ ] **Debug mode off** — `DEBUG=false` in prod env. FastAPI's `/docs` may be disabled.
- [ ] **Dependency audit** — No known CVEs in installed packages.
  ```bash
  pip install pip-audit
  pip-audit
  ```
- [ ] **Container runs as non-root**:
  ```dockerfile
  USER 1000:1000
  ```
- [ ] **Read-only filesystem where possible** — Worker can write to `/tmp` only.

---

## Sign-off

| Check | Owner | Date | Status |
|---|---|---|---|
| HTTPS / TLS | Infra | | ☐ |
| Secrets | Backend | | ☐ |
| Monitoring | SRE | | ☐ |
| Backup | DBA | | ☐ |
| Health checks | Backend | | ☐ |
| Staging gate | QA | | ☐ |
| Scaling | Infra | | ☐ |
| Logging | SRE | | ☐ |
| Disaster recovery | SRE | | ☐ |
| Alerting | SRE | | ☐ |
