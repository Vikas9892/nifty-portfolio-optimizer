FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# requirements.prod.txt lives at backend/requirements.prod.txt (repo-root context)
COPY backend/requirements.prod.txt ./requirements.prod.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.prod.txt

# Copy entire repo: backend/ and src/ both land under /app/
COPY . .

RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

RUN chmod +x /app/backend/scripts/entrypoint.sh

ENTRYPOINT ["/app/backend/scripts/entrypoint.sh"]
