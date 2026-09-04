"""InMemoryInvestigationStore: create / get / update semantics."""

from datetime import UTC, datetime

import pytest

from app.domain.store import InMemoryInvestigationStore, InvestigationRecord
from app.engine.records import Chain
from app.engine.result import TraceParams, TraceStatus


def _record(trace_id: str = "t1") -> InvestigationRecord:
    return InvestigationRecord(
        trace_id=trace_id,
        case_id=None,
        start_address="Tx",
        chain=Chain.TRON,
        params=TraceParams(),
        status=TraceStatus.QUEUED,
        created_at=datetime.now(UTC),
    )


def test_create_then_get():
    store = InMemoryInvestigationStore()
    rec = _record()
    store.create(rec)
    assert store.get("t1") is rec
    assert store.get("missing") is None


def test_create_is_idempotent_guarded():
    store = InMemoryInvestigationStore()
    store.create(_record())
    with pytest.raises(KeyError):
        store.create(_record())


def test_update_replaces_the_record():
    store = InMemoryInvestigationStore()
    rec = _record()
    store.create(rec)
    rec.status = TraceStatus.DONE
    store.update(rec)
    assert store.get("t1").status is TraceStatus.DONE
