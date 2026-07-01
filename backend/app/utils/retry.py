"""Retry and circuit-breaker utilities for external service calls (Yahoo Finance, etc.)."""

from __future__ import annotations

import time
from collections.abc import Callable
from enum import StrEnum
from threading import Lock
from typing import Any

from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from backend.app.utils.logger import logger

# ── Tenacity retry decorator ──────────────────────────────────────────────────


def with_retry(attempts: int = 3, wait_min: float = 1.0, wait_max: float = 10.0) -> Callable:
    """Decorator: retry up to `attempts` times with exponential back-off."""
    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
        before_sleep=before_sleep_log(logger, 20),  # 20 = logging.INFO
        reraise=True,
    )


# ── Circuit breaker ────────────────────────────────────────────────────────────


class CircuitState(StrEnum):
    CLOSED = "closed"  # Normal — calls pass through
    OPEN = "open"  # Tripped — calls rejected immediately
    HALF_OPEN = "half_open"  # Probing — one call allowed to test recovery


class CircuitBreaker:
    """
    Thread-safe circuit breaker.

    State machine:
        CLOSED  → OPEN      after `fail_max` consecutive failures
        OPEN    → HALF_OPEN after `reset_timeout` seconds
        HALF_OPEN → CLOSED  on success
        HALF_OPEN → OPEN    on failure
    """

    def __init__(self, name: str, fail_max: int = 5, reset_timeout: int = 60) -> None:
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            if self._state == CircuitState.OPEN:
                elapsed = time.monotonic() - (self._opened_at or 0)
                if elapsed >= self.reset_timeout:
                    self._state = CircuitState.HALF_OPEN
                    logger.info("CIRCUIT[%s] | → HALF_OPEN (testing recovery)", self.name)
                else:
                    remaining = int(self.reset_timeout - elapsed)
                    raise RuntimeError(
                        f"Circuit '{self.name}' is OPEN — service unavailable. "
                        f"Retry in ~{remaining}s."
                    )

        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            with self._lock:
                self._failures += 1
                if self._failures >= self.fail_max or self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.OPEN
                    self._opened_at = time.monotonic()
                    logger.error(
                        "CIRCUIT[%s] | → OPEN after %d failures | last: %s",
                        self.name,
                        self._failures,
                        exc,
                    )
            raise

        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("CIRCUIT[%s] | → CLOSED (service recovered)", self.name)
            self._state = CircuitState.CLOSED
            self._failures = 0

        return result


# ── Singletons ─────────────────────────────────────────────────────────────────

yahoo_breaker = CircuitBreaker(name="yahoo-finance", fail_max=5, reset_timeout=60)
