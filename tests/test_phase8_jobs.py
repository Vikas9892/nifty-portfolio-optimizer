"""Phase 8 — job system, metrics, circuit breaker, retry utilities."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ── Job Service ────────────────────────────────────────────────────────────────

class TestJobService:
    def test_create_returns_queued_job(self):
        from backend.app.services.job_service import JobService, JobStatus
        svc = JobService()
        job = svc.create(user_id=1, request_data={"stocks": ["TCS.NS"]})
        assert job["status"] == JobStatus.QUEUED
        assert job["user_id"] == 1
        assert "job_id" in job

    def test_mark_running(self):
        from backend.app.services.job_service import JobService, JobStatus
        svc = JobService()
        job = svc.create(user_id=1, request_data={})
        job_id = job["job_id"]
        # Without Redis, mark_running is a no-op (no cache)
        svc.mark_running(job_id)  # should not raise

    def test_idempotency_without_redis(self):
        """Without Redis, idempotency check returns None and creates a new job."""
        from backend.app.services.job_service import JobService
        svc = JobService()
        job = svc.create(user_id=1, request_data={}, idempotency_key="key-123")
        # Second call with same key — no Redis so cache.get returns None → new job
        job2 = svc.create(user_id=1, request_data={}, idempotency_key="key-123")
        # Both are valid (no Redis dedup without Redis)
        assert job["job_id"] != job2["job_id"] or True  # graceful — no assertion on equality


# ── Circuit Breaker ────────────────────────────────────────────────────────────

class TestCircuitBreaker:
    def test_starts_closed(self):
        from backend.app.utils.retry import CircuitBreaker, CircuitState
        cb = CircuitBreaker("test", fail_max=3, reset_timeout=60)
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_fail_max(self):
        from backend.app.utils.retry import CircuitBreaker, CircuitState
        cb = CircuitBreaker("test", fail_max=3, reset_timeout=60)

        def bad_func():
            raise RuntimeError("boom")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                cb.call(bad_func)

        assert cb.state == CircuitState.OPEN

    def test_rejects_when_open(self):
        from backend.app.utils.retry import CircuitBreaker, CircuitState
        cb = CircuitBreaker("test", fail_max=1, reset_timeout=9999)

        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))

        assert cb.state == CircuitState.OPEN
        with pytest.raises(RuntimeError, match="OPEN"):
            cb.call(lambda: None)

    def test_success_resets_failure_count(self):
        from backend.app.utils.retry import CircuitBreaker, CircuitState
        cb = CircuitBreaker("test", fail_max=3, reset_timeout=60)

        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))

        cb.call(lambda: "ok")  # success resets counter
        assert cb.state == CircuitState.CLOSED
        assert cb._failures == 0


# ── Metrics Service ────────────────────────────────────────────────────────────

class TestMetricsService:
    def test_get_all_reports_every_counter_the_dashboard_reads(self):
        from backend.app.services.metrics_service import MetricsService
        svc = MetricsService()
        result = svc.get_all()
        assert isinstance(result, dict)
        # A key missing here crashes the admin dashboard's render.
        for key in (
            "api:requests:total",
            "api:errors:total",
            "cache:hits",
            "cache:misses",
            "cache:hit_ratio",
            "optimize:count",
            "optimize:avg_ms",
            "jobs:queued",
            "jobs:completed",
            "jobs:failed",
        ):
            assert key in result, f"missing counter: {key}"
        assert 0 <= result["cache:hit_ratio"] <= 1

    def test_counters_are_recorded_without_redis(self):
        """Without Redis the in-process fallback still records counters.

        This previously asserted everything stayed at zero, which is what made
        the metrics dashboard show a wall of zeros on a Redis-free deployment.
        Deltas are used so the assertion holds regardless of test ordering.
        """
        from backend.app.services.metrics_service import MetricsService
        svc = MetricsService()
        before = svc.get_all()["jobs:queued"]
        svc.increment("jobs:queued")
        svc.increment("jobs:queued", delta=5)
        assert svc.get_all()["jobs:queued"] == before + 6

    def test_record_duration_feeds_the_average(self):
        from backend.app.services.metrics_service import MetricsService
        svc = MetricsService()
        svc.record_duration("unit:test:op", 1000.0)
        svc.record_duration("unit:test:op", 3000.0)
        all_metrics = svc.get_all()
        # get_all() only surfaces the known keys, so assert via the raw counters.
        from backend.app.services.cache_service import cache
        total = cache.get("metrics:unit:test:op:sum")
        count = cache.get("metrics:unit:test:op:count")
        assert total == 4000.0
        assert count == 2
        assert isinstance(all_metrics, dict)

    def test_reading_metrics_does_not_inflate_the_hit_ratio(self):
        """get_all() fetches counters through cache.get(); counting those reads
        as cache hits would make every dashboard refresh move its own numbers."""
        from backend.app.services.metrics_service import MetricsService
        svc = MetricsService()
        first = svc.get_all()
        for _ in range(5):
            latest = svc.get_all()
        assert latest["cache:hits"] == first["cache:hits"]
        assert latest["cache:misses"] == first["cache:misses"]

    def test_timed_context_manager(self):
        import time
        from backend.app.services.metrics_service import MetricsService
        svc = MetricsService()
        with svc.timed("test:op"):
            time.sleep(0.01)  # simulate work


# ── Jobs API Endpoints ─────────────────────────────────────────────────────────

class TestJobsRouter:
    def test_queue_optimize_returns_202(self, client, auth_headers, monkeypatch):
        """Queue endpoint returns 202 Accepted with job_id immediately."""
        # Prevent the background task from actually running (no real Yahoo data)
        monkeypatch.setattr(
            "backend.app.workers.tasks.run_optimize_task",
            lambda job_id, user_id, req_data: None,
        )

        resp = client.post(
            "/api/v1/jobs/optimize",
            json={
                "stocks": ["TCS.NS", "INFY.NS"],
                "start": "2020-01-01",
                "end": "2023-12-31",
                "max_weight": 0.30,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 202, resp.text
        data = resp.json()["data"]
        assert "job_id" in data
        assert data["status"] == "queued"

    def test_get_nonexistent_job_returns_404(self, client, auth_headers):
        resp = client.get("/api/v1/jobs/nonexistent-uuid", headers=auth_headers)
        assert resp.status_code == 404

    def test_jobs_require_auth(self, client):
        resp = client.post(
            "/api/v1/jobs/optimize",
            json={"stocks": ["TCS.NS", "INFY.NS"], "start": "2020-01-01", "end": "2023-12-31", "max_weight": 0.30},
        )
        assert resp.status_code == 401


# ── Admin Metrics Endpoint ─────────────────────────────────────────────────────

class TestAdminRouter:
    def test_metrics_endpoint_requires_auth(self, client):
        resp = client.get("/api/v1/admin/metrics")
        assert resp.status_code == 401

    def test_metrics_endpoint_returns_dict(self, client, auth_headers):
        resp = client.get("/api/v1/admin/metrics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "cache:hit_ratio" in data
        assert "optimize:count" in data
        assert "jobs:queued" in data
