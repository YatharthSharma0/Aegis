"""Logging setup: plain lines in dev, one JSON object per line in production.

Every record carries the current ``request_id`` (from a context var the
request-id middleware sets), so a log line ties back to an HTTP call.
"""

from __future__ import annotations

import contextvars
import json
import logging
from datetime import UTC, datetime
from typing import Any

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "aegis_request_id", default="-"
)

_STD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for key, value in record.__dict__.items():
            if key not in _STD and key != "request_id":
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(*, json_output: bool, level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())
    if json_output:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-5s [%(request_id)s] %(name)s: %(message)s")
        )

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # uvicorn's own handlers would double-log; let them propagate to root.
    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(noisy).handlers[:] = []
        logging.getLogger(noisy).propagate = True
