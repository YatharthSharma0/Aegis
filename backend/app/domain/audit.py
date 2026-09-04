"""The audit log: append hash-chained rows, read them back, verify the chain.

Append is atomic — reading the previous ``row_hash`` and inserting the new row
happen in one transaction (a Postgres advisory lock serialises concurrent
appends; SQLite serialises writes anyway), so the chain can't fork.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from app.security.audit import GENESIS_HASH, HASHED_FIELDS, compute_row_hash


@dataclass(frozen=True)
class AuditActor:
    id: str | None = None
    role: str | None = None


SYSTEM_ACTOR = AuditActor()  # unauthenticated / background origin


@dataclass(frozen=True)
class AuditEntryView:
    seq: int
    ts: datetime
    actor_id: str | None
    actor_role: str | None
    action: str
    trace_id: str | None
    case_id: str | None
    address: str | None
    chain: str | None
    detail: dict[str, Any] | None
    result_hash: str | None
    request_id: str | None
    prev_row_hash: str
    row_hash: str

    def hashed_fields(self) -> dict[str, object]:
        return {key: getattr(self, key) for key in HASHED_FIELDS}


@dataclass(frozen=True)
class AuditVerification:
    ok: bool
    checked: int
    broken_at_seq: int | None = None
    reason: str | None = None


class AuditStore(Protocol):
    def append(
        self, *, ts: datetime, fields: dict[str, Any], hasher: Callable[[str], str]
    ) -> None: ...
    def list(
        self, *, limit: int, action: str | None, actor_id: str | None
    ) -> Sequence[AuditEntryView]: ...
    def iter_chain(self) -> Sequence[AuditEntryView]: ...


class AuditService:
    def __init__(self, store: AuditStore) -> None:
        self._store = store

    def record(  # noqa: PLR0913 — an audit row has many optional facets
        self,
        action: str,
        *,
        actor: AuditActor = SYSTEM_ACTOR,
        trace_id: str | None = None,
        case_id: str | None = None,
        address: str | None = None,
        chain: str | None = None,
        detail: dict[str, Any] | None = None,
        result_hash: str | None = None,
        request_id: str | None = None,
    ) -> None:
        ts = datetime.now(UTC)
        fields: dict[str, Any] = {
            "ts": ts,
            "actor_id": actor.id,
            "actor_role": actor.role,
            "action": action,
            "trace_id": trace_id,
            "case_id": case_id,
            "address": address,
            "chain": chain,
            "detail": detail,
            "result_hash": result_hash,
            "request_id": request_id,
        }
        self._store.append(
            ts=ts, fields=fields, hasher=lambda prev: compute_row_hash(prev, fields)
        )

    def list(
        self, *, limit: int = 100, action: str | None = None, actor_id: str | None = None
    ) -> list[AuditEntryView]:
        return list(self._store.list(limit=limit, action=action, actor_id=actor_id))

    def verify(self) -> AuditVerification:
        prev = GENESIS_HASH
        checked = 0
        for entry in self._store.iter_chain():
            checked += 1
            if entry.prev_row_hash != prev:
                return AuditVerification(
                    False, checked, entry.seq, "prev_row_hash does not chain"
                )
            expected = compute_row_hash(prev, entry.hashed_fields())
            if expected != entry.row_hash:
                return AuditVerification(
                    False, checked, entry.seq, "row_hash does not match its content"
                )
            prev = entry.row_hash
        return AuditVerification(True, checked)
