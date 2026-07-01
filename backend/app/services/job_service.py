"""Job lifecycle management backed by Redis (falls back to no-op when Redis is absent)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from backend.app.services.cache_service import cache
from backend.app.utils.logger import logger

_JOB_TTL = 3600  # 1 hour


class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobService:
    def _key(self, job_id: str) -> str:
        return f"job:{job_id}"

    def create(
        self,
        user_id: int,
        request_data: dict,
        idempotency_key: str | None = None,
    ) -> dict:
        # Idempotency: return the existing job if this key was seen before
        if idempotency_key:
            existing_id = cache.get(f"idempotency:{idempotency_key}")
            if existing_id:
                existing = self.get(str(existing_id))
                if existing:
                    logger.info(
                        "JOB | idempotent hit key=%s job_id=%s", idempotency_key, existing_id
                    )
                    return existing

        job_id = str(uuid.uuid4())
        job: dict[str, Any] = {
            "job_id": job_id,
            "user_id": user_id,
            "status": JobStatus.QUEUED,
            "created_at": datetime.now(UTC).isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "request": request_data,
        }
        cache.set(self._key(job_id), job, ttl=_JOB_TTL)

        if idempotency_key:
            cache.set(f"idempotency:{idempotency_key}", job_id, ttl=_JOB_TTL)

        logger.info("JOB | created job_id=%s user_id=%s", job_id, user_id)
        return job

    def get(self, job_id: str) -> dict | None:
        return cache.get(self._key(job_id))

    def _update(self, job_id: str, updates: dict) -> None:
        job = self.get(job_id)
        if job:
            job.update(updates)
            cache.set(self._key(job_id), job, ttl=_JOB_TTL)

    def mark_running(self, job_id: str) -> None:
        self._update(
            job_id,
            {
                "status": JobStatus.RUNNING,
                "started_at": datetime.now(UTC).isoformat(),
            },
        )
        logger.info("JOB | running job_id=%s", job_id)

    def mark_completed(self, job_id: str, result: dict) -> None:
        self._update(
            job_id,
            {
                "status": JobStatus.COMPLETED,
                "completed_at": datetime.now(UTC).isoformat(),
                "result": result,
            },
        )
        from backend.app.services.metrics_service import metrics

        metrics.increment("jobs:completed")

    def mark_failed(self, job_id: str, error: str) -> None:
        self._update(
            job_id,
            {
                "status": JobStatus.FAILED,
                "completed_at": datetime.now(UTC).isoformat(),
                "error": error,
            },
        )
        from backend.app.services.metrics_service import metrics

        metrics.increment("jobs:failed")
        logger.error("JOB | failed job_id=%s error=%s", job_id, error)
