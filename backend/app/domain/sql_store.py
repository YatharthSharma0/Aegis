"""SQLAlchemy-backed :class:`~app.domain.store.InvestigationStore`.

The full engine ``Investigation`` is stored as JSON; ``result_hash`` is stored
alongside so it can be re-verified against a recomputed hash without rehydrating.
Rehydration is strict — a stored row that no longer validates against the current
engine schema raises rather than returning a half-built record.
"""

from __future__ import annotations

from app.db.engine import session_scope
from app.db.models import TraceRun
from app.domain.store import InvestigationRecord
from app.engine.records import Chain
from app.engine.result import Investigation, TraceParams, TraceStatus


class SqlInvestigationStore:
    def create(self, record: InvestigationRecord) -> None:
        with session_scope() as session:
            session.add(_to_row(record))

    def get(self, trace_id: str) -> InvestigationRecord | None:
        with session_scope() as session:
            row = session.get(TraceRun, trace_id)
            return _to_record(row) if row is not None else None

    def update(self, record: InvestigationRecord) -> None:
        with session_scope() as session:
            row = session.get(TraceRun, record.trace_id)
            if row is None:
                session.add(_to_row(record))
                return
            _apply(record, row)


def _to_row(record: InvestigationRecord) -> TraceRun:
    row = TraceRun(id=record.trace_id)
    _apply(record, row)
    return row


def _apply(record: InvestigationRecord, row: TraceRun) -> None:
    row.case_id = record.case_id
    row.start_address = record.start_address
    row.chain = record.chain.value
    row.params = record.params.model_dump(mode="json")
    row.status = record.status.value
    row.created_at = record.created_at
    row.started_at = record.started_at
    row.finished_at = record.finished_at
    row.investigation = (
        record.investigation.model_dump(mode="json")
        if record.investigation is not None
        else None
    )
    row.result_hash = (
        record.investigation.result_hash() if record.investigation is not None else None
    )
    row.error = record.error


def _to_record(row: TraceRun) -> InvestigationRecord:
    investigation = (
        Investigation.model_validate(row.investigation)
        if row.investigation is not None
        else None
    )
    return InvestigationRecord(
        trace_id=row.id,
        case_id=row.case_id,
        start_address=row.start_address,
        chain=Chain(row.chain),
        params=TraceParams.model_validate(row.params),
        status=TraceStatus(row.status),
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
        investigation=investigation,
        error=row.error,
    )
