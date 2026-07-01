"""Structured logging — text format in dev, JSON in prod (LOG_FORMAT=json)."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime


class _JSONFormatter(logging.Formatter):
    """Emits one JSON object per log line with standard SRE-friendly fields."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Thread-through correlation ID when set by RequestIDMiddleware
        if hasattr(record, "request_id"):
            entry["request_id"] = record.request_id
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def _build_logger(name: str) -> logging.Logger:
    lg = logging.getLogger(name)
    if lg.handlers:
        return lg

    lg.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    use_json = os.getenv("LOG_FORMAT", "text").lower() == "json"
    if use_json:
        handler.setFormatter(_JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    lg.addHandler(handler)
    lg.propagate = False
    return lg


# One shared logger for the whole backend — import this everywhere
logger = _build_logger("nifty")
