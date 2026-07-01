"""
Cache-aside service backed by Redis.
Falls back gracefully to a no-op when Redis is unavailable or REDIS_URL is unset.

Usage:
    from backend.app.services.cache_service import cache

    cached = cache.get("key")
    if cached is None:
        value = expensive_operation()
        cache.set("key", value, ttl=300)

Cache key conventions:
    stocks:universe                 — full stock universe (TTL 1 h)
    portfolio:history:<user_id>     — user's portfolio list (TTL 2 min)
    portfolio:<portfolio_id>        — individual portfolio detail (TTL 5 min)
    job:<job_id>                    — async job state (TTL 1 h)
    metrics:<counter>               — performance counters (TTL 7 days)
"""

from __future__ import annotations

import contextlib
import json
import os
from typing import Any

from backend.app.utils.logger import logger


class CacheService:
    def __init__(self) -> None:
        self._client = None
        self._ok = False
        self._connect()

    def _connect(self) -> None:
        url = os.getenv("REDIS_URL", "")
        if not url:
            logger.info("CACHE | REDIS_URL not configured — running cache-free")
            return
        try:
            import redis  # noqa: PLC0415

            client = redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
            client.ping()
            self._client = client
            self._ok = True
            logger.info("CACHE | Redis connected")
        except Exception as exc:
            logger.warning("CACHE | Redis unavailable (%s) — running cache-free", exc)

    # ── Core get/set/delete ───────────────────────────────────────────────────

    def get(self, key: str) -> Any | None:
        if not self._ok:
            return None
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
            return
        with contextlib.suppress(Exception):
            self._client.setex(key, ttl, json.dumps(value, default=str))

    def delete(self, key: str) -> None:
        if not self._ok:
            return
        with contextlib.suppress(Exception):
            self._client.delete(key)

    def invalidate_prefix(self, prefix: str) -> None:
        """Delete all keys matching `prefix:*`. Uses KEYS — avoid on hot paths."""
        if not self._ok:
            return
        try:
            keys = self._client.keys(f"{prefix}:*")
            if keys:
                self._client.delete(*keys)
        except Exception:
            pass

    # ── Atomic counters (for metrics and rate limiting) ───────────────────────

    def increment(self, key: str, delta: int = 1, ttl: int = 86_400) -> int:
        """Atomic integer increment. Returns new value (0 if Redis unavailable)."""
        if not self._ok:
            return 0
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
            return 0.0
        try:
            pipe = self._client.pipeline()
            pipe.incrbyfloat(key, delta)
            pipe.expire(key, ttl)
            return float(pipe.execute()[0])
        except Exception:
            return 0.0

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _track_hit(self) -> None:
        with contextlib.suppress(Exception):
            if self._ok:
                self._client.incr("metrics:cache:hits")

    def _track_miss(self) -> None:
        with contextlib.suppress(Exception):
            if self._ok:
                self._client.incr("metrics:cache:misses")


cache = CacheService()
