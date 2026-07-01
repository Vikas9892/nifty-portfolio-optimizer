"""
Redis-based distributed lock (Milestone 5).

Uses the SET NX EX pattern — the only correct primitive for this in Redis.
Release uses a Lua compare-and-delete to ensure we only release our own lock.

Usage:
    from backend.app.services.distributed_lock import acquire_lock

    with acquire_lock("market-refresh", ttl=300) as acquired:
        if not acquired:
            return  # another instance holds the lock
        # ... do work ...

Interview answer for "why distributed lock?":
    Prevent duplicate scheduler runs across multiple FastAPI replicas.
    Without a lock, two replicas firing at the same time both refresh Yahoo Finance
    and write the same rows to Postgres, wasting quota and adding write contention.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from contextlib import contextmanager

from backend.app.utils.logger import logger

# Lua script: only delete key if its value matches our token (compare-and-delete).
# This prevents releasing another holder's lock if ours expired.
_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class DistributedLock:
    """Thin wrapper around Redis SET NX EX for mutual exclusion across replicas."""

    def __init__(self, name: str, ttl: int = 30) -> None:
        self.name = name
        self.ttl = ttl
        self._key = f"lock:{name}"
        self._token: str | None = None
        self._client = None

    def _get_client(self):
        if self._client is None:
            import os

            import redis as redis_lib

            url = os.getenv("REDIS_URL", "")
            if not url:
                return None
            try:
                self._client = redis_lib.from_url(url, socket_connect_timeout=2)
            except Exception:
                return None
        return self._client

    def acquire(self) -> bool:
        client = self._get_client()
        if client is None:
            # No Redis → lock trivially acquired (single instance)
            logger.debug("LOCK[%s] | acquired (no Redis — single instance assumed)", self.name)
            return True
        self._token = str(uuid.uuid4())
        acquired = bool(client.set(self._key, self._token, nx=True, ex=self.ttl))
        if acquired:
            logger.debug("LOCK[%s] | acquired (ttl=%ds)", self.name, self.ttl)
        else:
            logger.debug("LOCK[%s] | not acquired — another instance holds it", self.name)
        return acquired

    def release(self) -> None:
        client = self._get_client()
        if client is None or self._token is None:
            return
        try:
            client.eval(_RELEASE_SCRIPT, 1, self._key, self._token)
            logger.debug("LOCK[%s] | released", self.name)
        except Exception as exc:
            logger.warning("LOCK[%s] | release failed: %s", self.name, exc)
        finally:
            self._token = None


@contextmanager
def acquire_lock(name: str, ttl: int = 30) -> Generator[bool, None, None]:
    """Context manager that acquires a lock and releases it on exit."""
    lock = DistributedLock(name, ttl=ttl)
    acquired = lock.acquire()
    try:
        yield acquired
    finally:
        if acquired:
            lock.release()
