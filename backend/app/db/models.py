"""ORM models. One table per Phase 2 concern, added as each PR lands.

``trace_runs`` (persistence PR), ``users`` + ``refresh_tokens`` (auth PR),
``audit_log`` (audit PR). ``cases`` / ``complaints`` arrive with case management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# BIGINT isn't a rowid alias on SQLite (so it won't autoincrement); use INTEGER there.
_AutoBigInt = BigInteger().with_variant(Integer, "sqlite")


class TraceRun(Base):
    __tablename__ = "trace_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    case_id: Mapped[str | None] = mapped_column(String(64), index=True)
    start_address: Mapped[str] = mapped_column(String(128), nullable=False)
    chain: Mapped[str] = mapped_column(String(16), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Durable-queue bookkeeping (set by a worker when it claims the row).
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    worker_id: Mapped[str | None] = mapped_column(String(64))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Full engine Investigation as JSON (Investigation.model_dump(mode="json")).
    investigation: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    result_hash: Mapped[str | None] = mapped_column(String(128))
    error: Mapped[str | None] = mapped_column(String(512))


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # officer|analyst|admin
    unit: Mapped[str | None] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RefreshToken(Base):
    """One issued refresh token. Rotation revokes the old row and inserts a new one."""

    __tablename__ = "refresh_tokens"

    jti: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditEntry(Base):
    """Append-only, hash-chained record of authenticated state changes and
    evidentiary reads. ``row_hash`` chains to ``prev_row_hash`` so any mutation,
    deletion, insertion, or reorder of a committed row is detectable.

    The application role must be granted INSERT + SELECT only on this table in
    production (Postgres GRANT); the code never issues UPDATE/DELETE here.
    """

    __tablename__ = "audit_log"

    seq: Mapped[int] = mapped_column(_AutoBigInt, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(32), index=True)
    actor_role: Mapped[str | None] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(32), index=True)
    case_id: Mapped[str | None] = mapped_column(String(64))
    address: Mapped[str | None] = mapped_column(String(128))
    chain: Mapped[str | None] = mapped_column(String(16))
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    result_hash: Mapped[str | None] = mapped_column(String(128))
    request_id: Mapped[str | None] = mapped_column(String(32))
    prev_row_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
