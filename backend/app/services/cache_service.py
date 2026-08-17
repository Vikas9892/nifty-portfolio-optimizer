"""
Cache-aside service backed by Redis.

Falls back to a bounded in-process store when Redis is unavailable or REDIS_URL
is unset, so single-instance deployments (Render free tier: WORKERS=1) keep
working. Async job state lives here, and a no-op store made every
`GET /api/v1/jobs/{job_id}` return 404 immediately after the job was created.

The fallback is per-process and therefore only correct while a single worker is
running. With WORKERS>1 each worker gets its own view, so a poll can land on a
worker that never saw the job — configure Redis for any multi-worker deployment.

Usage:
    from backend.app.services.cache_service import cache

    cached = cache.get("key")
    if cached is None:
        value = expensive_operation()
        cache.set("key", value, ttl=300)

Cache key conventions:
    stocks:universe                 — full stock universe (TTL 1 h)
    portfolio:history:<user_id>     — user's portfolio list (TTL 2 min)
    portfolio:<user_id>:<id>        — portfolio detail, scoped to its owner (TTL 5 min)
    job:<job_id>                    — async job state (TTL 1 h)
    metrics:<counter>               — performance counters (TTL 7 days)
"""

from __future__ import annotations

import contextlib
import json
import os
import threading
import time
from typing import Any

from backend.app.utils.logger import logger

# Cap on the in-process fallback so a long-running instance cannot grow without
# bound. Entries are evicted by soonest expiry once the cap is reached.
_MEM_MAX_ENTRIES = 1_000


class CacheService:
    def __init__(self) -> None:
        self._client = None
        self._ok = False
        # key -> (expires_at_monotonic, raw_json). Values are stored as JSON, exactly
        # as the Redis path does, so both backends round-trip types identically.
        self._mem: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()
        self._connect()

    def _connect(self) -> None:
        url = os.getenv("REDIS_URL", "")
        if not url:
            logger.info("CACHE | REDIS_URL not configured — using in-process store")
            return
        try:
            import redis  # noqa: PLC0415

            client = redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
            client.ping()
            self._client = client
            self._ok = True
            logger.info("CACHE | Redis connected")
        except Exception as exc:
            logger.warning("CACHE | Redis unavailable (%s) — using in-process store", exc)

    # ── In-process fallback ───────────────────────────────────────────────────

    def _mem_get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            entry = self._mem.get(key)
            if entry is None:
                return None
            expires_at, raw = entry
            if expires_at <= now:
                del self._mem[key]
                return None
        return json.loads(raw)

    def _mem_set(self, key: str, value: Any, ttl: int) -> None:
        raw = json.dumps(value, default=str)
        now = time.monotonic()
        with self._lock:
            # Drop anything already expired before considering the cap.
            expired = [k for k, (exp, _) in self._mem.items() if exp <= now]
            for k in expired:
                del self._mem[k]
            if key not in self._mem and len(self._mem) >= _MEM_MAX_ENTRIES:
                oldest = min(self._mem, key=lambda k: self._mem[k][0])
                del self._mem[oldest]
            self._mem[key] = (now + ttl, raw)

    # ── Core get/set/delete ───────────────────────────────────────────────────

    def get(self, key: str) -> Any | None:
        if not self._ok:
            return self._mem_get(key)
        try:
            raw = self._client.get(key)
            if raw is None:
                self._track_miss()
                return None
            self._track_hit()
            return json.loads(raw)
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if not self._ok:
            self._mem_set(key, value, ttl)
            return
        with contextlib.suppress(Exception):
            self._client.setex(key, ttl, json.dumps(value, default=str))

    def delete(self, key: str) -> None:
        if not self._ok:
            with self._lock:
                self._mem.pop(key, None)
            return
        with contextlib.suppress(Exception):
            self._client.delete(key)

    def invalidate_prefix(self, prefix: str) -> None:
        """Delete all keys matching `prefix:*`. Uses KEYS — avoid on hot paths."""
        if not self._ok:
            with self._lock:
                for k in [k for k in self._mem if k.startswith(f"{prefix}:")]:
                    del self._mem[k]
            return
        try:
            keys = self._client.keys(f"{prefix}:*")
            if keys:
                self._client.delete(*keys)
        except Exception:
            pass

    # ── Atomic counters (for metrics and rate limiting) ───────────────────────

    def increment(self, key: str, delta: int = 1, ttl: int = 86_400) -> int:
        """Atomic integer increment. Returns the new value."""
        if not self._ok:
            return int(self._mem_increment(key, delta, ttl))
        try:
            pipe = self._client.pipeline()
            pipe.incrby(key, delta)
            pipe.expire(key, ttl)
            return int(pipe.execute()[0])
        except Exception:
            return 0

    def increment_float(self, key: str, delta: float, ttl: int = 86_400) -> float:
        """Atomic float increment via INCRBYFLOAT. Returns new value."""
        if not self._ok:
            return float(self._mem_increment(key, delta, ttl))
        try:
            pipe = self._client.pipeline()
            pipe.incrbyfloat(key, delta)
            pipe.expire(key, ttl)
            return float(pipe.execute()[0])
        except Exception:
            return 0.0

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _mem_increment(self, key: str, delta: float, ttl: int) -> float:
        """Increment under the same lock that guards reads, so concurrent
        BackgroundTasks threads cannot interleave a read-modify-write."""
        now = time.monotonic()
        with self._lock:
            entry = self._mem.get(key)
            current = 0.0
            if entry is not None and entry[0] > now:
                with contextlib.suppress(ValueError, TypeError):
                    current = float(json.loads(entry[1]))
            new_value = current + delta
            self._mem[key] = (now + ttl, json.dumps(new_value))
        return new_value

    def _track_hit(self) -> None:
        with contextlib.suppress(Exception):
            if self._ok:
                self._client.incr("metrics:cache:hits")

    def _track_miss(self) -> None:
        with contextlib.suppress(Exception):
            if self._ok:
                self._client.incr("metrics:cache:misses")


cache = CacheService()
