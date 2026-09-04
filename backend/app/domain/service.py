"""``TraceService`` — the trace lifecycle: start (queue), execute, read.

``start_trace`` only persists a ``queued`` row; a worker (:mod:`app.worker`)
claims it via ``store.claim_next`` and calls ``execute``. Storage is behind
:class:`InvestigationStore`; the engine behind :func:`app.engine_bridge.run_engine`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.errors import InvalidTraceRequestError, TraceNotFoundError
from app.domain.schemas import TraceRequest
from app.domain.store import InvestigationRecord, InvestigationStore
from app.engine.errors import AddressFormatError
from app.engine.records import Chain
from app.engine.result import TraceStatus
from app.engine.tron import validate_tron_address
from app.engine_bridge import run_engine


def _now() -> datetime:
    return datetime.now(UTC)


class TraceService:
    def __init__(self, store: InvestigationStore) -> None:
        self._store = store

    @property
    def store(self) -> InvestigationStore:
        return self._store

    def start_trace(self, request: TraceRequest) -> InvestigationRecord:
        if request.chain is not Chain.TRON:
            raise InvalidTraceRequestError(
                f"chain {request.chain.value} is not supported yet",
                details={"supported": ["tron"]},
            )
        try:
            address = validate_tron_address(request.address)
        except AddressFormatError as exc:
            raise InvalidTraceRequestError(
                str(exc), details={"address": request.address}
            ) from exc

        record = InvestigationRecord(
            trace_id=uuid.uuid4().hex,
            case_id=request.case_id,
            start_address=address,
            chain=request.chain,
            params=request.params.to_engine(),
            status=TraceStatus.QUEUED,
            created_at=_now(),
        )
        self._store.create(record)
        return record

    def run_next(
        self, *, worker_id: str = "local", lease_s: float = 120.0, max_attempts: int = 3
    ) -> InvestigationRecord | None:
        """Claim and execute one pending trace. Convenience for the inline path
        and tests; the standalone worker adds audit around this.
        """
        record = self._store.claim_next(worker_id, lease_s)
        if record is None:
            return None
        return self.execute(record, max_attempts=max_attempts)

    def execute(self, record: InvestigationRecord, *, max_attempts: int) -> InvestigationRecord:
        """Run the engine for an already-claimed (``running``) record and persist
        its terminal state. A record over ``max_attempts`` is failed, not retried.
        """
        if record.attempts > max_attempts:
            record.status = TraceStatus.FAILED
            record.error = f"gave up after {record.attempts - 1} failed attempts"
        else:
            try:
                investigation = run_engine(
                    record.start_address, record.chain, record.params
                )
                record.investigation = investigation
                record.status = investigation.status
                record.error = None
            except Exception as exc:  # any engine failure becomes a failed trace
                record.status = TraceStatus.FAILED
                record.error = f"{type(exc).__name__}: {exc}"
        record.finished_at = _now()
        record.lease_expires_at = None
        self._store.update(record)
        return record

    def get(self, trace_id: str) -> InvestigationRecord:
        record = self._store.get(trace_id)
        if record is None:
            raise TraceNotFoundError(trace_id)
        return record
