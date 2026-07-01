"""Background task implementations — run by FastAPI BackgroundTasks (dev) or RQ worker (prod)."""

from __future__ import annotations

import time

from backend.app.utils.logger import logger


def run_optimize_task(job_id: str, user_id: int, request_data: dict) -> dict:
    """
    Portfolio optimization task.
    Called by FastAPI BackgroundTasks in development or an RQ worker in production.
    Lazy imports keep the worker process lightweight.
    """
    from backend.app.models import database as db
    from backend.app.schemas.auth import UserResponse
    from backend.app.schemas.portfolio import OptimizeRequest
    from backend.app.services.job_service import JobService
    from backend.app.services.metrics_service import metrics
    from backend.app.services.portfolio_service import PortfolioService

    job_service = JobService()
    job_service.mark_running(job_id)

    start = time.perf_counter()
    logger.info("WORKER | job_id=%s user_id=%s STARTED", job_id, user_id)

    try:
        req = OptimizeRequest(**request_data)
        user_row = db.get_user_by_id(user_id)
        if not user_row:
            raise ValueError(f"User {user_id} not found")

        user = UserResponse(
            id=user_row["id"],
            name=user_row["name"],
            email=user_row["email"],
            created_at=user_row["created_at"],
            is_active=bool(user_row["is_active"]),
        )

        result = PortfolioService().optimize(req, user)
        elapsed_ms = (time.perf_counter() - start) * 1000

        metrics.record_duration("optimize:duration", elapsed_ms)
        metrics.increment("optimize:count")

        result_dict = result.model_dump()
        job_service.mark_completed(job_id, result_dict)

        logger.info(
            "WORKER | job_id=%s COMPLETED sharpe=%.2f elapsed_ms=%.0f",
            job_id,
            result.sharpe,
            elapsed_ms,
        )
        return result_dict

    except Exception as exc:
        job_service.mark_failed(job_id, str(exc))
        logger.error("WORKER | job_id=%s FAILED: %s", job_id, exc, exc_info=True)
        raise
