# Deploying the backend to Render (free tier)

Replaces the previous Railway deployment. Total cost: **₹0**.

| Component | Provider | Free tier limits |
| --- | --- | --- |
| Backend API | Render Web Service | 512 MB RAM, 750 instance-hours/mo, spins down after 15 min idle |
| PostgreSQL | Neon | 0.5 GB storage, no expiry |
| Redis | *(not deployed)* | App runs cache-free; add later if needed |
| Frontend | Vercel | unchanged |

---

## 1. Create the Neon database (~2 min)

Render's own free Postgres is **deleted after 30 days**, which is why the blueprint
does not provision one. Neon's free tier has no expiry.

1. Sign up at <https://neon.tech> (GitHub login works).
2. Create a project — name it `nifty-optimizer`, region **AWS ap-southeast-1 (Singapore)**
   to match the Render region.
3. On the project dashboard, copy the **connection string**. It looks like:

   ```
   postgresql://neondb_owner:AbC123@ep-cool-name-12345678.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```

   Keep this tab open — you need it in step 3.

> The app auto-rewrites a `postgres://` prefix to `postgresql://`
> (`backend/app/core/config.py:28`), so either form works.

**Status: done.** The database is provisioned and verified — PostgreSQL 18.4 on
`ap-southeast-1`, TLS 1.3, with all 7 tables (`users`, `refresh_tokens`,
`portfolios`, `portfolio_weights`, `prices`, `jobs`, `audit_logs`) already
created and empty. `init_all_tables()` is idempotent, so the app re-running it
on first boot is a no-op.

---

## 2. Create the Render service from the blueprint

1. Push the current branch so `render.yaml` is on GitHub:

   ```bash
   git add render.yaml backend/Dockerfile .github/workflows/deploy.yml docs/RENDER_DEPLOY.md
   git commit -m "deploy: migrate backend from Railway to Render free tier"
   git push origin main
   ```

2. Go to <https://dashboard.render.com/blueprints> → **New Blueprint Instance**.
3. Connect your GitHub account and pick the `nifty-portfolio-optimizer` repo.
4. Render reads `render.yaml` and shows one service: **nifty-optimizer-api**.
5. It prompts for the two `sync: false` variables — fill them in now (step 3),
   then click **Apply**.

> **Alternative (no blueprint):** New → Web Service → connect repo → Language
> **Docker** → Root Directory `backend` → Dockerfile Path `backend/Dockerfile`
> → Instance Type **Free** → then add every env var from step 3 by hand.

---

## 3. Environment variables

Set these under **Environment** in the Render dashboard:

| Key | Value |
| --- | --- |
| `DATABASE_URL` | the Neon connection string from step 1 |
| `CORS_ORIGINS` | `https://<your-app>.vercel.app` (comma-separated for several) |

Already set for you by `render.yaml` — no action needed:

| Key | Value | Why |
| --- | --- | --- |
| `ENVIRONMENT` | `production` | |
| `WORKERS` | `1` | 2 uvicorn workers OOM in 512 MB once pandas/numpy load |
| `SCHEDULER_ENABLED` | `false` | free instances sleep, so APScheduler can't fire reliably |
| `LOG_FORMAT` | `json` | structured logs |
| `JWT_SECRET_KEY` | auto-generated, stable across deploys | |
| `REDIS_URL` | empty | app degrades to cache-free |

---

## 4. Verify

The first build takes **5–10 minutes** (numpy, pandas, pyportfolioopt wheels).
Watch **Logs** in the dashboard. You want to see:

```
==> Starting Uvicorn on 0.0.0.0:10000 with 1 worker(s)...
STARTUP | DATABASE_URL scheme: postgresql***
STARTUP | Database tables ready
STARTUP | Nifty Portfolio Optimizer v4.0.0 ready (production)
```

Then, from your machine:

```bash
BASE=https://nifty-optimizer-api.onrender.com

curl $BASE/health     # {"status":"healthy",...}
curl $BASE/ready      # {"status":"ready","db":"ok"}   ← confirms Neon is wired up
curl $BASE/version
open $BASE/docs       # Swagger UI
```

If `/ready` returns `503 {"db":"unreachable"}`, `DATABASE_URL` is wrong — check
that `?sslmode=require` is present.

---

## 5. Point the frontend at Render

```bash
# frontend/.env  (local dev — leave as localhost)
VITE_API_URL=http://localhost:8000
```

For the deployed frontend, set the production env var in **Vercel → Project →
Settings → Environment Variables**:

```
VITE_API_URL = https://nifty-optimizer-api.onrender.com
```

Then redeploy the frontend. Finally, make sure that Vercel URL is in
`CORS_ORIGINS` on Render (step 3) — otherwise the browser blocks every request.

If you deploy the frontend via GitHub Actions instead, set the repo variable
`VITE_API_URL` (Settings → Secrets and variables → Actions → Variables), which
`deploy.yml` passes as a Docker build arg.

---

## 6. CI/CD

`render.yaml` sets `autoDeploy: true`, so **every push to `main` redeploys
automatically** — nothing else required.

Optional, if you'd rather have CI gate the deploy:

1. Render dashboard → service → **Settings** → **Deploy Hook** → copy the URL.
2. GitHub repo → Settings → Secrets and variables → Actions → **New repository
   secret** → `RENDER_DEPLOY_HOOK` = that URL.
3. Set `autoDeploy: false` in `render.yaml`.

For the smoke-test job, set the repo **variable** `BACKEND_URL` to
`https://nifty-optimizer-api.onrender.com`.

---

## Free-tier caveats

- **Cold starts.** After 15 minutes with no traffic the instance sleeps; the next
  request takes **~50 seconds**. Warn users, or ping `/health` every 10 minutes
  from a free cron (e.g. <https://cron-job.org>) to keep it warm. That does burn
  your 750 monthly instance-hours, which is enough for exactly one always-on
  service — fine here, since this is the only one.
- **No persistent disk.** SQLite would reset on every deploy. That's precisely
  why the database lives on Neon.
- **512 MB RAM.** Keep `WORKERS=1`. If you see the process getting killed mid-
  request, an optimization run over many tickers is the likely cause.
- **Async job endpoints** (`/api/v1/jobs/*`) and caching return a degraded
  response while `REDIS_URL` is empty. To enable them, create a free
  <https://upstash.com> Redis, paste its URL into `REDIS_URL`, and redeploy —
  no code change needed.

---

## Rolling back to Railway

`railway.toml` is still in the repo and unchanged. If you ever restore the
subscription, `railway up --service backend` works exactly as before.
