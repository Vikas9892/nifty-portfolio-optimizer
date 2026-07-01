"""
SRE observability endpoints (Phase 9).

GET  /api/v1/sre/circuit-breakers    — all breaker states (M2)
GET  /api/v1/sre/feature-flags       — all runtime flags (M4)
PUT  /api/v1/sre/feature-flags/{flag} — toggle a flag (M4)
GET  /api/v1/sre/dlq                 — inspect dead letter queue (M7)
POST /api/v1/sre/dlq/{job_id}/retry  — re-queue a DLQ job (M7)
DELETE /api/v1/sre/dlq/{job_id}      — discard a DLQ entry (M7)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.routers.auth import get_current_user
from backend.app.schemas.auth import UserResponse

router = APIRouter(prefix="/api/v1/sre", tags=["SRE"])


# ── Circuit breakers (M2) ─────────────────────────────────────────────────────


@router.get("/circuit-breakers", summary="All circuit breaker states")
def list_circuit_breakers(_: UserResponse = Depends(get_current_user)) -> dict:
    from backend.app.utils.retry import get_all_breaker_states

    return {"breakers": get_all_breaker_states()}


# ── Feature flags (M4) ────────────────────────────────────────────────────────


class FlagUpdate(BaseModel):
    enabled: bool


@router.get("/feature-flags", summary="All feature flag values")
def list_feature_flags(_: UserResponse = Depends(get_current_user)) -> dict:
    from backend.app.services.feature_flags import flags

    return {"flags": flags.get_all()}


@router.put("/feature-flags/{flag}", summary="Set a feature flag at runtime")
def set_feature_flag(
    flag: str,
    body: FlagUpdate,
    _: UserResponse = Depends(get_current_user),
) -> dict:
    from backend.app.services.feature_flags import flags

    try:
        flags.set(flag, body.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"flag": flag, "enabled": body.enabled}


@router.delete("/feature-flags/{flag}", summary="Reset a flag to its default")
def reset_feature_flag(flag: str, _: UserResponse = Depends(get_current_user)) -> dict:
    from backend.app.services.feature_flags import flags

    flags.reset(flag)
    return {"flag": flag, "reset": True}


# ── Dead Letter Queue (M7) ────────────────────────────────────────────────────


@router.get("/dlq", summary="Inspect the dead letter queue")
def inspect_dlq(
    limit: int = 50,
    _: UserResponse = Depends(get_current_user),
) -> dict:
    from backend.app.services.dlq_service import dlq

    jobs = dlq.list_jobs(limit=limit)
    return {"count": len(jobs), "jobs": jobs}


@router.post("/dlq/{job_id}/retry", summary="Re-queue a failed DLQ job")
def retry_dlq_job(job_id: str, _: UserResponse = Depends(get_current_user)) -> dict:
    """
    Moves the job snapshot back to the active job store with status=queued
    and removes it from the DLQ. The caller must re-trigger the job via
    POST /api/v1/jobs/optimize with the same request body.
    """
    from backend.app.services.dlq_service import dlq
    from backend.app.services.job_service import JobService, JobStatus

    snapshot = dlq.get_job(job_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not in DLQ"
        )

    job_service = JobService()
    # Reset to queued so the caller can re-submit
    from backend.app.services.cache_service import cache

    restored = {**snapshot, "status": JobStatus.QUEUED, "retry_count": 0, "error": None}
    cache.set(job_service._key(job_id), restored, ttl=3600)
    dlq.remove(job_id)

    return {
        "job_id": job_id,
        "status": "re-queued",
        "message": "Resubmit via POST /api/v1/jobs/optimize",
    }


@router.delete("/dlq/{job_id}", summary="Discard a DLQ entry permanently")
def discard_dlq_job(job_id: str, _: UserResponse = Depends(get_current_user)) -> dict:
    from backend.app.services.dlq_service import dlq

    if not dlq.get_job(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not in DLQ"
        )
    dlq.remove(job_id)
    return {"job_id": job_id, "discarded": True}
