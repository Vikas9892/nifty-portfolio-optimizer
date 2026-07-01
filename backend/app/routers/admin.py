"""Admin endpoints — system metrics, queue depth, performance dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.dependencies import get_current_user
from backend.app.schemas.auth import UserResponse
from backend.app.schemas.response import SuccessResponse
from backend.app.services.metrics_service import metrics

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.get(
    "/metrics",
    summary="System performance metrics",
    description=(
        "Aggregate runtime metrics: cache hit ratio, average optimization latency (ms), "
        "job queue depth, request counts, error counts. Backed by Redis counters."
    ),
)
def get_metrics(
    current_user: UserResponse = Depends(get_current_user),
) -> SuccessResponse[dict]:
    data = metrics.get_all()

    # Enrich with live RQ queue depth when Redis is available
    try:
        from backend.app.core.config import settings

        if settings.has_redis:
            import redis as redis_lib
            from rq import Queue

            r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
            q = Queue(settings.job_queue_name, connection=r)
            data["queue:depth"] = len(q)
    except Exception:
        data["queue:depth"] = 0

    return SuccessResponse(message="Metrics fetched.", data=data)
