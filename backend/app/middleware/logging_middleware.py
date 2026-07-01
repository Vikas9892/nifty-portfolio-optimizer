"""Structured request/response logging with request-ID tracing."""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.services.metrics_service import metrics
from backend.app.utils.logger import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        request_id = getattr(request.state, "request_id", "-")

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "req_id=%s %s %s %d %.1fms | %s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request.client.host if request.client else "unknown",
        )

        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"

        # Track request metrics (skip health/metrics endpoints to avoid noise)
        path = request.url.path
        if path not in ("/health", "/ready", "/metrics", "/version"):
            metrics.increment("api:requests:total")
            if response.status_code >= 500:
                metrics.increment("api:errors:total")

        return response
