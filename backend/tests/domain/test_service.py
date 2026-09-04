"""TraceService lifecycle: queue -> run -> terminal state."""

import pytest

from app.domain.errors import InvalidTraceRequestError, TraceNotFoundError
from app.domain.schemas import TraceParamsIn, TraceRequest
from app.domain.service import TraceService
from app.domain.store import InMemoryInvestigationStore
from app.engine.records import Chain
from app.engine.result import TraceStatus

SEED = "TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC"


@pytest.fixture
def service() -> TraceService:
    return TraceService(InMemoryInvestigationStore())


def test_start_trace_queues_a_record(service: TraceService):
    rec = service.start_trace(TraceRequest(address=SEED, case_id="FIR-1"))
    assert rec.status is TraceStatus.QUEUED
    assert rec.case_id == "FIR-1"
    assert rec.start_address == SEED
    assert len(rec.trace_id) == 32
    assert service.get(rec.trace_id) is rec


def test_run_trace_reaches_done_with_a_result(service: TraceService):
    rec = service.start_trace(TraceRequest(address=SEED))
    service.run_next()
    done = service.get(rec.trace_id)
    assert done.status is TraceStatus.DONE
    assert done.started_at is not None and done.finished_at is not None
    assert done.investigation is not None
    assert done.investigation.result_hash().startswith("aegis.engine.v1:")
    names = [c.name for c in done.investigation.result.vasp_candidates]
    assert "DemoExchange" in names


def test_invalid_address_is_a_400_domain_error(service: TraceService):
    with pytest.raises(InvalidTraceRequestError):
        service.start_trace(TraceRequest(address="not-a-tron-address"))


def test_unsupported_chain_rejected(service: TraceService):
    with pytest.raises(InvalidTraceRequestError):
        service.start_trace(TraceRequest(address=SEED, chain=Chain.ETHEREUM))


def test_get_unknown_trace_raises_not_found(service: TraceService):
    with pytest.raises(TraceNotFoundError):
        service.get("does-not-exist")


def test_params_pass_through_to_the_engine(service: TraceService):
    rec = service.start_trace(
        TraceRequest(address=SEED, params=TraceParamsIn(max_hops=2))
    )
    service.run_next()
    done = service.get(rec.trace_id)
    assert done.params.max_hops == 2
    reasons = {e.reason.value for e in done.investigation.result.trail_events}
    assert "max_hops" in reasons
