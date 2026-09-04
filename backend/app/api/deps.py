"""Dependency wiring. One process-wide ``TraceService`` over the SQL store.

Tests override ``get_trace_service`` with an in-memory or SQLite-backed store.
"""

from __future__ import annotations

from functools import lru_cache

from app.domain.service import TraceService
from app.domain.sql_store import SqlInvestigationStore


@lru_cache
def get_trace_service() -> TraceService:
    return TraceService(SqlInvestigationStore())
