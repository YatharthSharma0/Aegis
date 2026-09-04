"""SQLAlchemy-backed :class:`~app.domain.audit.AuditStore`."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text

from app.db.engine import get_engine, session_scope
from app.db.models import AuditEntry
from app.domain.audit import AuditEntryView
from app.security.audit import GENESIS_HASH

# Arbitrary constant for the Postgres advisory lock that serialises appends.
_APPEND_LOCK_KEY = 0x4145_4749_5300_0001


class SqlAuditStore:
    def append(
        self, *, ts: datetime, fields: dict[str, Any], hasher: Callable[[str], str]
    ) -> None:
        with session_scope() as session:
            if get_engine().dialect.name == "postgresql":
                session.execute(
                    text("SELECT pg_advisory_xact_lock(:k)"), {"k": _APPEND_LOCK_KEY}
                )
            prev = session.scalar(
                select(AuditEntry.row_hash).order_by(AuditEntry.seq.desc()).limit(1)
            )
            prev_hash = prev or GENESIS_HASH
            session.add(
                AuditEntry(
                    ts=ts,
                    actor_id=fields.get("actor_id"),
                    actor_role=fields.get("actor_role"),
                    action=fields["action"],
                    trace_id=fields.get("trace_id"),
                    case_id=fields.get("case_id"),
                    address=fields.get("address"),
                    chain=fields.get("chain"),
                    detail=fields.get("detail"),
                    result_hash=fields.get("result_hash"),
                    request_id=fields.get("request_id"),
                    prev_row_hash=prev_hash,
                    row_hash=hasher(prev_hash),
                )
            )

    def list(
        self, *, limit: int, action: str | None, actor_id: str | None
    ) -> Sequence[AuditEntryView]:
        stmt = select(AuditEntry).order_by(AuditEntry.seq.desc()).limit(limit)
        if action is not None:
            stmt = stmt.where(AuditEntry.action == action)
        if actor_id is not None:
            stmt = stmt.where(AuditEntry.actor_id == actor_id)
        with session_scope() as session:
            return [_view(row) for row in session.scalars(stmt)]

    def iter_chain(self) -> Sequence[AuditEntryView]:
        with session_scope() as session:
            rows = session.scalars(select(AuditEntry).order_by(AuditEntry.seq.asc()))
            return [_view(row) for row in rows]


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _view(row: AuditEntry) -> AuditEntryView:
    return AuditEntryView(
        seq=row.seq,
        ts=_aware(row.ts),
        actor_id=row.actor_id,
        actor_role=row.actor_role,
        action=row.action,
        trace_id=row.trace_id,
        case_id=row.case_id,
        address=row.address,
        chain=row.chain,
        detail=row.detail,
        result_hash=row.result_hash,
        request_id=row.request_id,
        prev_row_hash=row.prev_row_hash,
        row_hash=row.row_hash,
    )
