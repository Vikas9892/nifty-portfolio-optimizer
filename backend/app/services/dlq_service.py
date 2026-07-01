"""
Dead Letter Queue service (Milestone 7).

When a job fails MAX_RETRIES times it is moved here instead of being silently dropped.
Admins can inspect failed jobs and manually retry or discard them.

Storage:
  Redis hash  job:<id>          — full job metadata (existing, from JobService)
  Redis list  dlq:index         — ordered list of job_ids in the DLQ
  Redis key   dlq:job:<id>      — copy of job snapshot at time of DLQ entry

Interview answer for "why DLQ?":
    Without a DLQ, failed jobs disappear. The operator has no way to know
    what data was lost or replay it after fixing the underlying bug.
    A DLQ turns silent data loss into an inspectable audit trail.
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.app.services.cache_service import cache
from backend.app.utils.logger import logger

MAX_RETRIES = 3  # jobs failing beyond this go to DLQ
_DLQ_TTL = 86_400 * 7  # keep DLQ jobs for 7 days
_DLQ_INDEX = "dlq:index"


class DLQService:
    def push(self, job: dict) -> None:
        """Move a permanently-failed job to the dead letter queue."""
        job_id = job.get("job_id", "unknown")
        snapshot = {**job, "dlq_at": datetime.now(UTC).isoformat()}

        # Store full snapshot
        cache.set(f"dlq:job:{job_id}", snapshot, ttl=_DLQ_TTL)

        # Append to index list via raw Redis (best-effort — no-op without Redis)
        self._lpush(_DLQ_INDEX, job_id)

        logger.error(
            "DLQ | job_id=%s user_id=%s moved to dead letter queue after %d failures",
            job_id,
            job.get("user_id"),
            job.get("retry_count", 0),
        )

    def list_jobs(self, limit: int = 50) -> list[dict]:
        """Return up to `limit` most recent DLQ job snapshots."""
        ids = self._lrange(_DLQ_INDEX, 0, limit - 1)
        jobs = []
        for jid in ids:
            job = cache.get(f"dlq:job:{jid}")
            if job:
                jobs.append(job)
        return jobs

    def get_job(self, job_id: str) -> dict | None:
        return cache.get(f"dlq:job:{job_id}")

    def remove(self, job_id: str) -> None:
        """Discard a DLQ entry (after manual inspection or re-queue)."""
        cache.delete(f"dlq:job:{job_id}")
        self._lrem(_DLQ_INDEX, job_id)
        logger.info("DLQ | job_id=%s removed", job_id)

    # ── Raw Redis helpers (graceful no-op without Redis) ──────────────────────

    def _lpush(self, key: str, value: str) -> None:
        client = self._client()
        if client:
            try:
                client.lpush(key, value)
                client.expire(key, _DLQ_TTL)
            except Exception:
                pass

    def _lrange(self, key: str, start: int, end: int) -> list[str]:
        client = self._client()
        if client:
            try:
                return [
                    v.decode() if isinstance(v, bytes) else v
                    for v in client.lrange(key, start, end)
                ]
            except Exception:
                pass
        return []

    def _lrem(self, key: str, value: str) -> None:
        client = self._client()
        if client:
            import contextlib

            with contextlib.suppress(Exception):
                client.lrem(key, 0, value)

    def _client(self):
        import os

        redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            return None
        try:
            import redis as redis_lib

            return redis_lib.from_url(redis_url, socket_connect_timeout=2)
        except Exception:
            return None


dlq = DLQService()
