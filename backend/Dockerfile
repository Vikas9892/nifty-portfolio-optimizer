# ── Backend Dockerfile ────────────────────────────────────────────────────────
# Multi-stage: install deps, then copy app. Python 3.12-slim for a small image.

FROM python:3.12-slim AS base

# System deps: libpq for psycopg2, gcc for native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies before copying source (layer-cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create data directory for SQLite (bind-mounted in docker-compose)
RUN mkdir -p data

EXPOSE 8000

# Liveness probe so Docker / Compose can restart unhealthy containers
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# scripts/entrypoint.sh waits for the DB then starts uvicorn
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
