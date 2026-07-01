"""
Redis-backed feature flag system (Milestone 4).

Flags are stored in Redis as `ff:<FLAG_NAME>` with a 24-hour TTL.
If Redis is absent, env-var defaults are used — the app always has a sensible fallback.

Usage:
    from backend.app.services.feature_flags import flags

    if flags.is_enabled("ENABLE_CACHE"):
        hit = cache.get(key)
"""

from __future__ import annotations

from backend.app.services.cache_service import cache
from backend.app.utils.logger import logger

# Canonical flag names — use these constants everywhere to avoid typos
ENABLE_CACHE = "ENABLE_CACHE"
ENABLE_WORKERS = "ENABLE_WORKERS"
ENABLE_SCHEDULER = "ENABLE_SCHEDULER"
ENABLE_METRICS = "ENABLE_METRICS"
ENABLE_PDF_REPORTS = "ENABLE_PDF_REPORTS"

# Default values — what the flag is worth when Redis has no override
_DEFAULTS: dict[str, bool] = {
    ENABLE_CACHE: True,
    ENABLE_WORKERS: True,
    ENABLE_SCHEDULER: True,
    ENABLE_METRICS: True,
    ENABLE_PDF_REPORTS: False,
}

_PREFIX = "ff"
_TTL = 86_400  # 24 hours — flags survive restarts but don't live forever


class FeatureFlags:
    """Runtime feature toggle system backed by Redis with env-var fallback."""

    def is_enabled(self, flag: str) -> bool:
        """Return True if the flag is enabled. Redis overrides env-var default."""
        raw = cache.get(f"{_PREFIX}:{flag}")
        if raw is not None:
            return bool(raw)
        default = _DEFAULTS.get(flag, False)
        return default

    def set(self, flag: str, enabled: bool) -> None:
        """Override a flag value at runtime. Stored in Redis for 24 h."""
        if flag not in _DEFAULTS:
            raise ValueError(f"Unknown feature flag: '{flag}'. Valid: {list(_DEFAULTS)}")
        cache.set(f"{_PREFIX}:{flag}", enabled, ttl=_TTL)
        logger.info("FEATURE_FLAG | %s → %s", flag, "enabled" if enabled else "disabled")

    def reset(self, flag: str) -> None:
        """Remove runtime override — falls back to env-var default."""
        cache.delete(f"{_PREFIX}:{flag}")
        logger.info("FEATURE_FLAG | %s reset to default (%s)", flag, _DEFAULTS.get(flag))

    def get_all(self) -> dict[str, bool]:
        """Return every flag's current effective value."""
        return {k: self.is_enabled(k) for k in _DEFAULTS}


flags = FeatureFlags()
