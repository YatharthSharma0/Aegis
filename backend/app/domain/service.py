"""``TraceService`` — the trace lifecycle: start, run, read.

The HTTP layer calls :meth:`start_trace` then schedules :meth:`run_trace` as a
background task. Storage is behind :class:`InvestigationStore`; the engine is
behind :func:`app.engine_bridge.run_engine`. Neither the transport nor the
engine internals leak into here.
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

    def start_trace(self, request: TraceRequest) -> InvestigationRecord:
        if request.chain is not Chain.TRON:
            raise InvalidTraceRequestError(
                f"chain {request.chain.value} is not supported yet",
                details={"supported": ["tron"]},
            )
        try:
            address = validate_tron_address(request.address)
        except AddressFormatError as exc:
            raise InvalidTraceRequestError(str(exc), details={"address": request.address}) from exc

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

    def run_trace(self, trace_id: str) -> None:
        """Background-task body: run the engine and persist the terminal state."""
        record = self._store.get(trace_id)
        if record is None:  # pragma: no cover - scheduled right after create
            return
        record.status = TraceStatus.RUNNING
        record.started_at = _now()
        self._store.update(record)
        try:
            investigation = run_engine(record.start_address, record.chain, record.params)
            record.investigation = investigation
            record.status = investigation.status
        except Exception as exc:  # any engine failure becomes a failed trace
            record.status = TraceStatus.FAILED
            record.error = f"{type(exc).__name__}: {exc}"
        record.finished_at = _now()
        self._store.update(record)

    def get(self, trace_id: str) -> InvestigationRecord:
        record = self._store.get(trace_id)
        if record is None:
            raise TraceNotFoundError(trace_id)
        return record
