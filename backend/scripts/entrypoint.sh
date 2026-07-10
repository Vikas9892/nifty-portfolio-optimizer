#!/bin/sh
set -e

WORKERS=${WORKERS:-1}
PORT=${PORT:-8000}

echo "==> Starting Uvicorn on 0.0.0.0:$PORT with $WORKERS worker(s)..."
exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$WORKERS" \
    --access-log
