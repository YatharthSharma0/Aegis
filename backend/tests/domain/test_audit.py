"""Audit log: chaining, verification, and tamper detection."""

from sqlalchemy import text

from app.db.engine import session_scope
from app.domain.audit import AuditActor, AuditService
from app.domain.audit_store import SqlAuditStore
from app.security.audit import GENESIS_HASH

OFFICER = AuditActor(id="u1", role="officer")


def _service() -> AuditService:
    return AuditService(SqlAuditStore())


def test_first_entry_chains_from_genesis():
    svc = _service()
    svc.record("trace.start", actor=OFFICER, trace_id="t1")
    entries = svc.list()
    assert len(entries) == 1
    assert entries[0].prev_row_hash == GENESIS_HASH
    assert entries[0].row_hash != GENESIS_HASH


def test_chain_links_each_row_to_the_previous():
    svc = _service()
    svc.record("trace.start", actor=OFFICER, trace_id="t1")
    svc.record("trace.read", actor=OFFICER, trace_id="t1")
    svc.record("trace.complete", actor=OFFICER, trace_id="t1", result_hash="aegis.engine.v1:x")

    chain = list(reversed(svc.list()))  # oldest first
    assert chain[1].prev_row_hash == chain[0].row_hash
    assert chain[2].prev_row_hash == chain[1].row_hash


def test_verify_passes_on_an_untouched_chain():
    svc = _service()
    for i in range(5):
        svc.record("trace.read", actor=OFFICER, trace_id=f"t{i}")
    result = svc.verify()
    assert result.ok is True
    assert result.checked == 5
    assert result.broken_at_seq is None


def test_verify_detects_a_mutated_row():
    svc = _service()
    svc.record("trace.start", actor=OFFICER, trace_id="t1")
    svc.record("trace.read", actor=OFFICER, trace_id="t1")
    svc.record("trace.read_graph", actor=OFFICER, trace_id="t1")

    # tamper with row 2's content directly, leaving its stored row_hash intact
    with session_scope() as session:
        session.execute(
            text("UPDATE audit_log SET address = 'INJECTED' WHERE seq = 2")
        )

    result = svc.verify()
    assert result.ok is False
    assert result.broken_at_seq == 2
    assert "row_hash" in (result.reason or "")


def test_verify_detects_a_deleted_row():
    svc = _service()
    for i in range(4):
        svc.record("trace.read", actor=OFFICER, trace_id=f"t{i}")
    with session_scope() as session:
        session.execute(text("DELETE FROM audit_log WHERE seq = 2"))

    result = svc.verify()
    assert result.ok is False
    assert result.broken_at_seq == 3  # the row after the gap no longer chains


def test_verify_detects_a_forged_appended_row():
    svc = _service()
    svc.record("trace.start", actor=OFFICER, trace_id="t1")
    svc.record("trace.complete", actor=OFFICER, trace_id="t1")
    with session_scope() as session:
        session.execute(
            text(
                "INSERT INTO audit_log "
                "(ts, action, trace_id, prev_row_hash, row_hash) VALUES "
                "(:ts, 'trace.read', 't1', :prev, :row)"
            ),
            {"ts": "2026-09-04 10:00:00.000000", "prev": "a" * 64, "row": "b" * 64},
        )
    result = svc.verify()
    assert result.ok is False
