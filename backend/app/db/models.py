"""ORM models. One table per Phase 2 concern, added as each PR lands.

This PR: ``trace_runs`` — the persisted trace lifecycle. ``users``, ``cases``,
``complaints`` and ``audit_log`` arrive with auth / cases / the audit log.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


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

    # Full engine Investigation as JSON (Investigation.model_dump(mode="json")).
    investigation: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    result_hash: Mapped[str | None] = mapped_column(String(128))
    error: Mapped[str | None] = mapped_column(String(512))
