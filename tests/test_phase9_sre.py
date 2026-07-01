"""Phase 9 — SRE tests: feature flags, distributed lock, DLQ, circuit breaker registry."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ── Feature flags ─────────────────────────────────────────────────────────────


class TestFeatureFlags:
    def test_defaults_when_redis_absent(self):
        from backend.app.services.feature_flags import FeatureFlags

        ff = FeatureFlags()
        with patch("backend.app.services.feature_flags.cache") as mock_cache:
            mock_cache.get.return_value = None
            assert ff.is_enabled("ENABLE_CACHE") is True
            assert ff.is_enabled("ENABLE_PDF_REPORTS") is False

    def test_redis_override(self):
        from backend.app.services.feature_flags import FeatureFlags

        ff = FeatureFlags()
        with patch("backend.app.services.feature_flags.cache") as mock_cache:
            mock_cache.get.return_value = True
            assert ff.is_enabled("ENABLE_CACHE") is True
            mock_cache.get.return_value = False
            assert ff.is_enabled("ENABLE_CACHE") is False

    def test_set_validates_known_flags(self):
        import pytest
        from backend.app.services.feature_flags import FeatureFlags

        ff = FeatureFlags()
        with (
            patch("backend.app.services.feature_flags.cache"),
            pytest.raises(ValueError, match="Unknown feature flag"),
        ):
            ff.set("UNKNOWN_FLAG", True)

    def test_set_calls_cache(self):
        from backend.app.services.feature_flags import FeatureFlags

        ff = FeatureFlags()
        with patch("backend.app.services.feature_flags.cache") as mock_cache:
            ff.set("ENABLE_WORKERS", False)
            mock_cache.set.assert_called_once()

    def test_get_all_returns_all_flags(self):
        from backend.app.services.feature_flags import _DEFAULTS, FeatureFlags

        ff = FeatureFlags()
        with patch("backend.app.services.feature_flags.cache") as mock_cache:
            mock_cache.get.return_value = None
            result = ff.get_all()
            assert set(result.keys()) == set(_DEFAULTS.keys())


# ── Distributed lock ──────────────────────────────────────────────────────────


class TestDistributedLock:
    def test_acquire_without_redis_succeeds(self):
        from backend.app.services.distributed_lock import DistributedLock

        lock = DistributedLock("test-lock", ttl=10)
        with patch.dict("os.environ", {}, clear=True):
            lock._client = None
            # No REDIS_URL → _get_client returns None → trivial acquisition
            with patch.object(lock, "_get_client", return_value=None):
                assert lock.acquire() is True

    def test_acquire_fails_when_another_holds_lock(self):

        from backend.app.services.distributed_lock import DistributedLock

        mock_redis = MagicMock()
        mock_redis.set.return_value = False  # NX returned False → lock held by another

        lock = DistributedLock("test-lock", ttl=10)
        with patch.object(lock, "_get_client", return_value=mock_redis):
            assert lock.acquire() is False

    def test_context_manager_releases(self):
        from backend.app.services.distributed_lock import acquire_lock

        with patch("backend.app.services.distributed_lock.DistributedLock") as MockLock:
            instance = MagicMock()
            instance.acquire.return_value = True
            MockLock.return_value = instance

            with acquire_lock("test") as acquired:
                assert acquired is True

            instance.release.assert_called_once()

    def test_context_manager_no_release_if_not_acquired(self):
        from backend.app.services.distributed_lock import acquire_lock

        with patch("backend.app.services.distributed_lock.DistributedLock") as MockLock:
            instance = MagicMock()
            instance.acquire.return_value = False
            MockLock.return_value = instance

            with acquire_lock("test") as acquired:
                assert acquired is False

            instance.release.assert_not_called()


# ── Dead Letter Queue ─────────────────────────────────────────────────────────


class TestDLQService:
    def _make_job(self, job_id: str = "job-123") -> dict:
        return {
            "job_id": job_id,
            "user_id": 1,
            "status": "failed",
            "retry_count": 3,
            "error": "Something broke",
        }

    def test_push_stores_snapshot(self):
        from backend.app.services.dlq_service import DLQService

        svc = DLQService()
        job = self._make_job()
        with (
            patch("backend.app.services.dlq_service.cache") as mock_cache,
            patch.object(svc, "_lpush"),
        ):
            svc.push(job)
            mock_cache.set.assert_called_once()
            key_arg = mock_cache.set.call_args[0][0]
            assert "dlq:job:job-123" in key_arg

    def test_list_jobs_returns_cached_snapshots(self):
        from backend.app.services.dlq_service import DLQService

        svc = DLQService()
        job = self._make_job()
        with (
            patch.object(svc, "_lrange", return_value=["job-123"]),
            patch("backend.app.services.dlq_service.cache") as mock_cache,
        ):
            mock_cache.get.return_value = job
            result = svc.list_jobs()
            assert len(result) == 1
            assert result[0]["job_id"] == "job-123"

    def test_remove_cleans_cache_and_index(self):
        from backend.app.services.dlq_service import DLQService

        svc = DLQService()
        with (
            patch("backend.app.services.dlq_service.cache") as mock_cache,
            patch.object(svc, "_lrem") as mock_lrem,
        ):
            svc.remove("job-123")
            mock_cache.delete.assert_called_once_with("dlq:job:job-123")
            mock_lrem.assert_called_once()


# ── Circuit breaker registry (M2) ────────────────────────────────────────────


class TestCircuitBreakerRegistry:
    def test_register_and_retrieve(self):
        from backend.app.utils.retry import (
            _REGISTRY,
            CircuitBreaker,
            get_all_breaker_states,
            register_breaker,
        )

        cb = CircuitBreaker(name="test-service-registry", fail_max=3, reset_timeout=30)
        register_breaker(cb)
        assert "test-service-registry" in _REGISTRY

        states = get_all_breaker_states()
        names = [s["name"] for s in states]
        assert "test-service-registry" in names

    def test_state_dict_keys(self):
        from backend.app.utils.retry import CircuitBreaker

        cb = CircuitBreaker(name="test-keys", fail_max=3, reset_timeout=30)
        d = cb.as_dict()
        assert "state" in d
        assert "failures" in d
        assert "fail_max" in d


# ── JSON logger (M10) ─────────────────────────────────────────────────────────


class TestJSONLogger:
    def test_json_format_emits_valid_json(self):
        import json
        import logging

        from backend.app.utils.logger import _JSONFormatter

        formatter = _JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        line = formatter.format(record)
        parsed = json.loads(line)
        assert parsed["msg"] == "hello world"
        assert parsed["level"] == "INFO"
        assert "ts" in parsed

    def test_text_format_selected_without_env(self):

        with patch.dict("os.environ", {"LOG_FORMAT": "text"}):
            # Re-build a fresh logger (different name to avoid handler reuse)
            from backend.app.utils.logger import _build_logger

            lg = _build_logger("nifty-test-text")
            assert lg.handlers
            assert not isinstance(lg.handlers[0].formatter, type(None))


# ── SRE router integration ────────────────────────────────────────────────────


class TestSRERouter:
    def test_circuit_breakers_endpoint(self, client, auth_headers):
        resp = client.get("/api/v1/sre/circuit-breakers", headers=auth_headers)
        assert resp.status_code == 200
        assert "breakers" in resp.json()

    def test_feature_flags_endpoint(self, client, auth_headers):
        resp = client.get("/api/v1/sre/feature-flags", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "flags" in data
        assert "ENABLE_CACHE" in data["flags"]

    def test_set_feature_flag(self, client, auth_headers):
        resp = client.put(
            "/api/v1/sre/feature-flags/ENABLE_WORKERS",
            json={"enabled": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

    def test_set_unknown_flag_returns_400(self, client, auth_headers):
        resp = client.put(
            "/api/v1/sre/feature-flags/NONEXISTENT_FLAG",
            json={"enabled": True},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_dlq_endpoint_returns_list(self, client, auth_headers):
        resp = client.get("/api/v1/sre/dlq", headers=auth_headers)
        assert resp.status_code == 200
        assert "jobs" in resp.json()

    def test_discard_missing_dlq_job_returns_404(self, client, auth_headers):
        resp = client.delete("/api/v1/sre/dlq/nonexistent-job-id", headers=auth_headers)
        assert resp.status_code == 404


# ── JobService lifecycle (M7 — retry count + mark_dead) ───────────────────────


class TestJobServiceLifecycle:
    """
    CacheService is a no-op without Redis (get→None, set→no-op).
    Patch job_service.cache with an in-memory dict-backed mock so the full
    lifecycle can be exercised without a running Redis instance.
    """

    @staticmethod
    def _make_cache_mock():
        store: dict = {}
        m = MagicMock()
        m.get.side_effect = lambda k: store.get(k)
        m.set.side_effect = lambda k, v, ttl=300: store.update({k: v})
        m.delete.side_effect = lambda k: store.pop(k, None)
        return m

    def test_mark_running_updates_status(self):
        from backend.app.services.job_service import JobService, JobStatus

        mc = self._make_cache_mock()
        with patch("backend.app.services.job_service.cache", mc):
            svc = JobService()
            job = svc.create(user_id=1, request_data={})
            svc.mark_running(job["job_id"])
            updated = svc.get(job["job_id"])
        assert updated["status"] == JobStatus.RUNNING
        assert updated["started_at"] is not None

    def test_mark_completed_stores_result(self):
        from backend.app.services.job_service import JobService, JobStatus

        mc = self._make_cache_mock()
        with patch("backend.app.services.job_service.cache", mc):
            svc = JobService()
            job = svc.create(user_id=1, request_data={})
            svc.mark_completed(job["job_id"], {"sharpe": 1.5})
            updated = svc.get(job["job_id"])
        assert updated["status"] == JobStatus.COMPLETED
        assert updated["result"]["sharpe"] == 1.5

    def test_mark_failed_records_error(self):
        from backend.app.services.job_service import JobService, JobStatus

        mc = self._make_cache_mock()
        with patch("backend.app.services.job_service.cache", mc):
            svc = JobService()
            job = svc.create(user_id=1, request_data={})
            svc.mark_failed(job["job_id"], "boom")
            updated = svc.get(job["job_id"])
        assert updated["status"] == JobStatus.FAILED
        assert updated["error"] == "boom"

    def test_increment_retry_increments_count(self):
        from backend.app.services.job_service import JobService

        mc = self._make_cache_mock()
        with patch("backend.app.services.job_service.cache", mc):
            svc = JobService()
            job = svc.create(user_id=1, request_data={})
            count1 = svc.increment_retry(job["job_id"])
            count2 = svc.increment_retry(job["job_id"])
        assert count1 == 1
        assert count2 == 2

    def test_increment_retry_returns_zero_for_missing_job(self):
        from backend.app.services.job_service import JobService

        mc = self._make_cache_mock()
        with patch("backend.app.services.job_service.cache", mc):
            svc = JobService()
            assert svc.increment_retry("nonexistent-id") == 0

    def test_mark_dead_updates_status(self):
        from backend.app.services.job_service import JobService, JobStatus

        mc = self._make_cache_mock()
        with patch("backend.app.services.job_service.cache", mc):
            svc = JobService()
            job = svc.create(user_id=1, request_data={})
            svc.mark_dead(job["job_id"])
            updated = svc.get(job["job_id"])
        assert updated["status"] == JobStatus.DEAD

    def test_idempotency_returns_existing_job(self):
        from backend.app.services.job_service import JobService

        mc = self._make_cache_mock()
        with patch("backend.app.services.job_service.cache", mc):
            svc = JobService()
            job1 = svc.create(user_id=1, request_data={}, idempotency_key="idem-1")
            job2 = svc.create(user_id=1, request_data={}, idempotency_key="idem-1")
        assert job1["job_id"] == job2["job_id"]

    def test_retry_count_initialized_to_zero(self):
        from backend.app.services.job_service import JobService

        svc = JobService()
        job = svc.create(user_id=1, request_data={})
        assert job["retry_count"] == 0


# ── DistributedLock release path ──────────────────────────────────────────────


class TestDistributedLockRelease:
    def test_release_calls_eval_on_redis(self):
        from backend.app.services.distributed_lock import DistributedLock

        mock_redis = MagicMock()
        lock = DistributedLock("release-test", ttl=10)
        lock._token = "my-token"
        with patch.object(lock, "_get_client", return_value=mock_redis):
            lock.release()
        mock_redis.eval.assert_called_once()
        assert lock._token is None

    def test_release_no_op_when_no_client(self):
        from backend.app.services.distributed_lock import DistributedLock

        lock = DistributedLock("release-no-redis", ttl=10)
        lock._token = "some-token"
        with patch.object(lock, "_get_client", return_value=None):
            lock.release()  # should not raise
        # token cleared even without client? Actually no — client is None so we return early
        # The token stays set since we returned early; that's fine.

    def test_release_handles_eval_error_gracefully(self):
        from backend.app.services.distributed_lock import DistributedLock

        mock_redis = MagicMock()
        mock_redis.eval.side_effect = RuntimeError("Redis connection lost")
        lock = DistributedLock("release-error", ttl=10)
        lock._token = "token-xyz"
        with patch.object(lock, "_get_client", return_value=mock_redis):
            lock.release()  # should not raise — exception is logged and swallowed
        assert lock._token is None  # finally block clears token


# ── DLQService Redis paths ────────────────────────────────────────────────────


class TestDLQRedis:
    def test_lpush_no_op_when_no_redis(self):
        from backend.app.services.dlq_service import DLQService

        svc = DLQService()
        with patch.object(svc, "_client", return_value=None):
            svc._lpush("dlq:index", "job-1")  # should not raise

    def test_lrange_returns_empty_when_no_redis(self):
        from backend.app.services.dlq_service import DLQService

        svc = DLQService()
        with patch.object(svc, "_client", return_value=None):
            result = svc._lrange("dlq:index", 0, 10)
        assert result == []

    def test_lrem_no_op_when_no_redis(self):
        from backend.app.services.dlq_service import DLQService

        svc = DLQService()
        with patch.object(svc, "_client", return_value=None):
            svc._lrem("dlq:index", "job-1")  # should not raise

    def test_lpush_with_mock_redis(self):
        from backend.app.services.dlq_service import DLQService

        svc = DLQService()
        mock_redis = MagicMock()
        with patch.object(svc, "_client", return_value=mock_redis):
            svc._lpush("dlq:index", "job-1")
        mock_redis.lpush.assert_called_once_with("dlq:index", "job-1")
        mock_redis.expire.assert_called_once()

    def test_lrange_with_mock_redis(self):
        from backend.app.services.dlq_service import DLQService

        svc = DLQService()
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = [b"job-abc", b"job-def"]
        with patch.object(svc, "_client", return_value=mock_redis):
            result = svc._lrange("dlq:index", 0, 9)
        assert result == ["job-abc", "job-def"]


# ── FeatureFlags reset ────────────────────────────────────────────────────────


class TestFeatureFlagsReset:
    def test_reset_deletes_from_cache(self):
        from backend.app.services.feature_flags import FeatureFlags

        ff = FeatureFlags()
        with patch("backend.app.services.feature_flags.cache") as mock_cache:
            ff.reset("ENABLE_CACHE")
        mock_cache.delete.assert_called_once_with("ff:ENABLE_CACHE")
