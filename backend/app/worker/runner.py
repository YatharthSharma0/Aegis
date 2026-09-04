"""``TraceWorker`` — claim → execute → persist → audit, in a loop."""

from __future__ import annotations

import logging
import threading
import uuid

from app.domain.audit import AuditService
from app.domain.service import TraceService
from app.engine.result import TraceStatus

logger = logging.getLogger("aegis.worker")


class TraceWorker:
    def __init__(  # noqa: PLR0913 — worker knobs
        self,
        service: TraceService,
        audit: AuditService,
        *,
        worker_id: str | None = None,
        lease_s: float = 120.0,
        max_attempts: int = 3,
        poll_s: float = 1.0,
    ) -> None:
        self._service = service
        self._audit = audit
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self._lease_s = lease_s
        self._max_attempts = max_attempts
        self._poll_s = poll_s

    def run_once(self) -> bool:
        """Claim and run one trace. Return whether any work was done."""
        record = self._service.store.claim_next(self.worker_id, self._lease_s)
        if record is None:
            return False

        self._audit.record(
            "trace.claimed",
            trace_id=record.trace_id,
            detail={"worker_id": self.worker_id, "attempt": record.attempts},
        )
        done = self._service.execute(record, max_attempts=self._max_attempts)
        action = "trace.complete" if done.status is not TraceStatus.FAILED else "trace.failed"
        self._audit.record(
            action,
            trace_id=done.trace_id,
            result_hash=done.investigation.result_hash() if done.investigation else None,
            detail={
                "status": done.status.value,
                "error": done.error,
                "worker_id": self.worker_id,
                "attempts": done.attempts,
            },
        )
        return True

    def run_forever(self, stop: threading.Event) -> None:
        logger.info("worker %s started", self.worker_id)
        while not stop.is_set():
            try:
                did_work = self.run_once()
            except Exception:  # a bad iteration must not kill the loop
                logger.exception("worker %s iteration failed", self.worker_id)
                did_work = False
            stop.wait(0 if did_work else self._poll_s)
        logger.info("worker %s stopped", self.worker_id)
