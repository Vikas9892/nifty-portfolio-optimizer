FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.prod.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.prod.txt

# Copy backend source into /app/backend/ so "from backend.X" imports resolve
COPY . /app/backend/

RUN mkdir -p /app/data

EXPOSE 8000

# PORT is injected by the platform (Render sets 10000); fall back to 8000 locally.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f "http://localhost:${PORT:-8000}/health" || exit 1

RUN chmod +x /app/backend/scripts/entrypoint.sh

ENTRYPOINT ["/app/backend/scripts/entrypoint.sh"]
