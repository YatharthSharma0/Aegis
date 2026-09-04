"""TraceWorker: claim, execute, persist, retry-on-lease-expiry, give-up."""

import threading
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.audit import AuditService
from app.domain.audit_store import SqlAuditStore
from app.domain.schemas import TraceRequest
from app.domain.service import TraceService
from app.domain.sql_store import SqlInvestigationStore
from app.domain.store import InvestigationRecord
from app.engine.records import Chain
from app.engine.result import TraceParams, TraceStatus
from app.worker import TraceWorker

SEED = "TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC"


@pytest.fixture
def service() -> TraceService:
    return TraceService(SqlInvestigationStore())


@pytest.fixture
def worker(service: TraceService) -> TraceWorker:
    return TraceWorker(
        service, AuditService(SqlAuditStore()),
        worker_id="w-test", lease_s=60, max_attempts=3, poll_s=0,
    )


def test_run_once_claims_and_completes_a_queued_trace(service: TraceService, worker: TraceWorker):
    rec = service.start_trace(TraceRequest(address=SEED))
    assert worker.run_once() is True

    done = service.get(rec.trace_id)
    assert done.status is TraceStatus.DONE
    assert done.worker_id == "w-test"
    assert done.attempts == 1
    assert done.finished_at is not None
    assert done.lease_expires_at is None
    assert done.investigation is not None


def test_run_once_returns_false_on_an_empty_queue(worker: TraceWorker):
    assert worker.run_once() is False


def test_claim_takes_the_oldest_first(service: TraceService, worker: TraceWorker):
    first = service.start_trace(TraceRequest(address=SEED))
    second = service.start_trace(TraceRequest(address=SEED))
    # make the second look newer
    second.created_at = first.created_at + timedelta(seconds=5)
    service.store.update(second)

    claimed = service.store.claim_next("w-test", 60)
    assert claimed.trace_id == first.trace_id


def test_a_lease_expired_running_row_is_reclaimed(service: TraceService, worker: TraceWorker):
    rec = InvestigationRecord(
        trace_id="stuck1", case_id=None, start_address=SEED, chain=Chain.TRON,
        params=TraceParams(), status=TraceStatus.RUNNING,
        created_at=datetime.now(UTC) - timedelta(minutes=10),
        started_at=datetime.now(UTC) - timedelta(minutes=10),
        attempts=1, worker_id="dead-worker",
        lease_expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    service.store.create(rec)

    assert worker.run_once() is True
    recovered = service.get("stuck1")
    assert recovered.status is TraceStatus.DONE
    assert recovered.attempts == 2
    assert recovered.worker_id == "w-test"


def test_a_fresh_lease_is_not_stolen(service: TraceService):
    rec = InvestigationRecord(
        trace_id="running1", case_id=None, start_address=SEED, chain=Chain.TRON,
        params=TraceParams(), status=TraceStatus.RUNNING,
        created_at=datetime.now(UTC), attempts=1, worker_id="w-other",
        lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    service.store.create(rec)
    assert service.store.claim_next("w-test", 60) is None


def test_run_forever_drains_then_honours_the_stop_event(
    service: TraceService, worker: TraceWorker
):
    rec = service.start_trace(TraceRequest(address=SEED))
    stop = threading.Event()

    thread = threading.Thread(target=worker.run_forever, args=(stop,), daemon=True)
    thread.start()
    try:
        deadline = datetime.now(UTC) + timedelta(seconds=5)
        while datetime.now(UTC) < deadline:
            if service.get(rec.trace_id).status is TraceStatus.DONE:
                break
        assert service.get(rec.trace_id).status is TraceStatus.DONE
    finally:
        stop.set()
        thread.join(timeout=5)
    assert not thread.is_alive()


def test_gives_up_after_max_attempts(service: TraceService, worker: TraceWorker):
    rec = InvestigationRecord(
        trace_id="cursed1", case_id=None, start_address=SEED, chain=Chain.TRON,
        params=TraceParams(), status=TraceStatus.RUNNING,
        created_at=datetime.now(UTC), attempts=3,  # 4th claim will exceed max_attempts=3
        lease_expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    service.store.create(rec)

    assert worker.run_once() is True
    failed = service.get("cursed1")
    assert failed.status is TraceStatus.FAILED
    assert "gave up" in (failed.error or "")
