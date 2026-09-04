"""Run the trace worker as a standalone process:  ``python -m app.worker``."""

from __future__ import annotations

import logging
import signal
import threading
from types import FrameType

from app.config import get_settings
from app.db.engine import create_all
from app.domain.audit import AuditService
from app.domain.audit_store import SqlAuditStore
from app.domain.service import TraceService
from app.domain.sql_store import SqlInvestigationStore
from app.worker.runner import TraceWorker


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    settings = get_settings()
    if settings.environment != "production":
        create_all()

    worker = TraceWorker(
        TraceService(SqlInvestigationStore()),
        AuditService(SqlAuditStore()),
        lease_s=settings.worker_lease_s,
        max_attempts=settings.worker_max_attempts,
        poll_s=settings.worker_poll_s,
    )
    stop = threading.Event()

    def _handle(_signum: int, _frame: FrameType | None) -> None:
        stop.set()

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)
    worker.run_forever(stop)


if __name__ == "__main__":
    main()
