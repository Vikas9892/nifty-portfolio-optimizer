#!/bin/sh
# ── Backend container entrypoint ─────────────────────────────────────────────
# Waits for the database to be reachable before starting Uvicorn.
set -e

echo "==> Checking database connectivity…"

# Poll until the DB responds (handles PostgreSQL startup delay)
MAX_RETRIES=30
RETRY_INTERVAL=2
n=0

until python - <<'PYEOF'
import os, sys
url = os.environ.get("DATABASE_URL", "sqlite:///data/portfolio.db")
if url.startswith("sqlite"):
    sys.exit(0)   # SQLite is always available
try:
    from sqlalchemy import create_engine, text
    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    sys.exit(0)
except Exception as e:
    print(f"  DB not ready: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
do
    n=$((n + 1))
    if [ "$n" -ge "$MAX_RETRIES" ]; then
        echo "==> ERROR: database did not become ready after $MAX_RETRIES attempts."
        exit 1
    fi
    echo "  Waiting for database… (attempt $n/$MAX_RETRIES)"
    sleep "$RETRY_INTERVAL"
done

echo "==> Database ready."

# Number of Uvicorn workers (default 1 for SQLite, 2+ for PostgreSQL)
WORKERS=${WORKERS:-1}
PORT=${PORT:-8000}

echo "==> Starting Uvicorn on 0.0.0.0:$PORT with $WORKERS worker(s)…"
exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$WORKERS" \
    --access-log
