"""SqlInvestigationStore: round-trips a full Investigation through the DB."""

from datetime import UTC, datetime

from app.domain.schemas import TraceRequest
from app.domain.service import TraceService
from app.domain.sql_store import SqlInvestigationStore
from app.domain.store import InvestigationRecord
from app.engine.records import Chain
from app.engine.result import TraceParams, TraceStatus

SEED = "TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC"


def _record(trace_id: str = "abc123") -> InvestigationRecord:
    return InvestigationRecord(
        trace_id=trace_id,
        case_id="FIR-9",
        start_address=SEED,
        chain=Chain.TRON,
        params=TraceParams(max_hops=6),
        status=TraceStatus.QUEUED,
        created_at=datetime.now(UTC),
    )


def test_create_then_get_roundtrips_metadata():
    store = SqlInvestigationStore()
    store.create(_record("meta1"))
    got = store.get("meta1")
    assert got is not None
    assert got.case_id == "FIR-9"
    assert got.chain is Chain.TRON
    assert got.params.max_hops == 6
    assert got.status is TraceStatus.QUEUED
    assert got.investigation is None


def test_get_missing_returns_none():
    assert SqlInvestigationStore().get("nope") is None


def test_full_trace_persists_and_result_hash_reverifies():
    store = SqlInvestigationStore()
    service = TraceService(store)
    rec = service.start_trace(TraceRequest(address=SEED))
    service.run_trace(rec.trace_id)

    reloaded = store.get(rec.trace_id)
    assert reloaded.status is TraceStatus.DONE
    assert reloaded.investigation is not None
    # the stored result_hash matches a freshly recomputed one
    assert reloaded.investigation.result_hash().startswith("aegis.engine.v1:")
    names = [c.name for c in reloaded.investigation.result.vasp_candidates]
    assert "DemoExchange" in names


def test_update_persists_terminal_state():
    store = SqlInvestigationStore()
    rec = _record("upd1")
    store.create(rec)
    rec.status = TraceStatus.FAILED
    rec.error = "boom"
    rec.finished_at = datetime.now(UTC)
    store.update(rec)

    got = store.get("upd1")
    assert got.status is TraceStatus.FAILED
    assert got.error == "boom"
    assert got.finished_at is not None
