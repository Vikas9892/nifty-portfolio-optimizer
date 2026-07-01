"""Async portfolio optimization — submit a job, poll for result."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, status

from backend.app.core.dependencies import get_current_user
from backend.app.schemas.auth import UserResponse
from backend.app.schemas.portfolio import OptimizeRequest
from backend.app.schemas.response import SuccessResponse
from backend.app.services.job_service import JobService, JobStatus
from backend.app.services.metrics_service import metrics
from backend.app.utils.exceptions import AuthorizationError, NotFoundError
from backend.app.utils.logger import logger

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])
_job_service = JobService()


def _enqueue(
    job_id: str,
    user_id: int,
    req_data: dict,
    background_tasks: BackgroundTasks,
) -> str:
    """
    Route the job to RQ when Redis is available; fall back to FastAPI BackgroundTasks.
    This graceful degradation means the app works in dev (no Redis) and prod (RQ worker).
    """
    from backend.app.core.config import settings
    from backend.app.workers.tasks import run_optimize_task

    if settings.has_redis:
        try:
            import redis as redis_lib
            from rq import Queue

            r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
            q = Queue(settings.job_queue_name, connection=r)
            q.enqueue(run_optimize_task, job_id, user_id, req_data, job_timeout=600)
            logger.info("JOB | enqueued via RQ job_id=%s queue=%s", job_id, settings.job_queue_name)
            return "rq"
        except Exception as exc:
            logger.warning("JOB | RQ unavailable (%s) — falling back to BackgroundTasks", exc)

    background_tasks.add_task(run_optimize_task, job_id, user_id, req_data)
    logger.info("JOB | enqueued via BackgroundTasks job_id=%s", job_id)
    return "background"


@router.post(
    "/optimize",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue an async portfolio optimization",
    description=(
        "Immediately returns a `job_id` (HTTP 202). The optimization runs in the background. "
        "Poll `GET /api/v1/jobs/{job_id}` until `status` is `completed` or `failed`. "
        "Supply `Idempotency-Key` to get the same job back on duplicate requests — safe to retry."
    ),
)
def queue_optimize(
    req: OptimizeRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> SuccessResponse[dict]:
    metrics.increment("jobs:queued")

    job = _job_service.create(
        user_id=current_user.id,
        request_data=req.model_dump(),
        idempotency_key=idempotency_key,
    )

    # Don't re-enqueue an idempotent hit that's already in-flight or done
    if job["status"] == JobStatus.QUEUED:
        _enqueue(job["job_id"], current_user.id, req.model_dump(), background_tasks)

    msg = (
        "Optimization queued — poll GET /api/v1/jobs/{job_id} for result."
        if job["status"] == JobStatus.QUEUED
        else f"Existing job returned (status={job['status']})."
    )
    return SuccessResponse(
        message=msg,
        data={"job_id": job["job_id"], "status": job["status"]},
    )


@router.get(
    "/{job_id}",
    summary="Poll job status",
    description=(
        "Returns the full job object. `result` is populated when `status=completed`. "
        "Recommended polling interval: 2 seconds."
    ),
)
def get_job(
    job_id: str,
    current_user: UserResponse = Depends(get_current_user),
) -> SuccessResponse[dict]:
    job = _job_service.get(job_id)
    if not job:
        raise NotFoundError("Job")
    if job["user_id"] != current_user.id:
        raise AuthorizationError("You don't own this job.")
    return SuccessResponse(message="Job fetched.", data=job)
