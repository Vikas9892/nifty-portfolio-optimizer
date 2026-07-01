"""In-process metrics collection backed by Redis (no-op when Redis is absent)."""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any

from backend.app.services.cache_service import cache

_NS = "metrics"  # Redis key namespace


class MetricsService:
    """Lightweight counter store. All values survive restarts via Redis persistence."""

    def increment(self, key: str, delta: int = 1) -> None:
        cache.increment(f"{_NS}:{key}", delta, ttl=86_400 * 7)

    def record_duration(self, key: str, duration_ms: float) -> None:
        self.increment(f"{key}:count")
        cache.increment_float(f"{_NS}:{key}:sum", duration_ms, ttl=86_400 * 7)

    @contextmanager
    def timed(self, key: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.record_duration(key, elapsed_ms)

    def get_all(self) -> dict[str, Any]:
        keys = [
            "api:requests:total",
            "api:errors:total",
            "cache:hits",
            "cache:misses",
            "optimize:count",
            "optimize:duration:sum",
            "optimize:duration:count",
            "jobs:queued",
            "jobs:completed",
            "jobs:failed",
        ]
        result: dict[str, Any] = {}
        for k in keys:
            raw = cache.get(f"{_NS}:{k}")
            try:
                result[k] = float(raw) if raw is not None else 0
            except (TypeError, ValueError):
                result[k] = 0

        # Derived metrics
        hit = result.get("cache:hits", 0)
        miss = result.get("cache:misses", 0)
        total_cache = hit + miss
        result["cache:hit_ratio"] = round(hit / total_cache, 3) if total_cache else 0

        opt_sum = result.get("optimize:duration:sum", 0)
        opt_count = result.get("optimize:duration:count", 0)
        result["optimize:avg_ms"] = round(opt_sum / opt_count, 1) if opt_count else 0

        return result


metrics = MetricsService()
