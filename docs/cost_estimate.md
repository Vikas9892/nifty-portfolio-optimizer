# Cost Estimate

*Monthly infrastructure cost for Nifty Portfolio Optimizer at different scales.*
*Prices as of mid-2025 — verify with provider dashboards before budgeting.*

---

## Tier 1: Hobby / Development (~$0–15/month)

| Service | Provider | Plan | Cost/month |
|---|---|---|---|
| Backend API | Railway | Hobby ($5 credit) | ~$3 |
| Frontend | Vercel | Free | $0 |
| Database | SQLite on Railway volume | Included | $0 |
| Redis | Railway Redis | Hobby | ~$0 (0.25GB) |
| Domain | Namecheap | .io domain | ~$1.50 amortized |
| **Total** | | | **~$5** |

**Limitations:** No SLA, no backups, sleeps on inactivity.

---

## Tier 2: Startup (~$80–120/month)

| Service | Provider | Plan | Cost/month |
|---|---|---|---|
| Backend (2 replicas) | Railway | Pro | ~$20 |
| Frontend + CDN | Vercel | Pro | $20 |
| PostgreSQL | Supabase | Pro (8GB) | $25 |
| Redis | Upstash | Pay-per-request | ~$5 |
| S3 (PDF exports, backups) | AWS S3 | Standard (10GB) | ~$0.25 |
| Prometheus + Grafana | Self-hosted on Railway | ~$5 | $5 |
| Alertmanager | Same host as Prometheus | Included | $0 |
| Domain + SSL | Namecheap + Let's Encrypt | ~$1.50 + $0 | ~$2 |
| **Total** | | | **~$77** |

---

## Tier 3: Growth (~$250–400/month)

| Service | Provider | Plan | Cost/month |
|---|---|---|---|
| Backend (4 replicas, HPA) | Railway / Render | Compute | ~$60 |
| Frontend + CDN | Vercel | Pro | $20 |
| PostgreSQL (read replica) | Supabase | Pro | $50 |
| Redis Cluster (persistent) | Upstash / Railway | Cluster | ~$30 |
| S3 (backups + PDF) | AWS S3 | Standard (100GB) | ~$2.50 |
| Prometheus + Grafana Cloud | Grafana Cloud | Free tier | $0 |
| Alertmanager | Grafana Cloud | Included | $0 |
| Workers (4 replicas) | Railway | Compute | ~$40 |
| Log aggregation | Papertrail / Logtail | Startup | ~$15 |
| **Total** | | | **~$218** |

---

## Cost Drivers

1. **Compute** — Each FastAPI replica + RQ worker pair costs ~$15–20/month on Railway.
2. **Database** — PostgreSQL is the second-largest cost. Use connection pooling (PgBouncer) to maximize utilization before upsizing.
3. **Redis** — Low cost unless you need persistence and cluster mode.
4. **Yahoo Finance** — Free tier (no official SLA). At scale, consider a paid market data provider (~$50–200/month for 50 tickers, EOD data).

---

## Cost Optimization Tips

- **Cache aggressively** — Each cache hit saves a DB round-trip and CPU time. Our 24h TTL already handles this well for daily EOD data.
- **Batch Yahoo Finance downloads** — ThreadPoolExecutor downloads groups in parallel; scheduler pre-warms cache daily so market-hours requests are pure cache hits.
- **SQLite for small deployments** — Free, no ops overhead, sufficient for < 100 concurrent users.
- **Serverless functions** — Portfolio optimization is CPU-bursty; AWS Lambda (arm64, 1–3GB) is cost-effective for < 1M calculations/month.
- **Spot/preemptible workers** — RQ workers are stateless and restart-safe (job persists in Redis). Use spot instances for 60–80% cost reduction.
