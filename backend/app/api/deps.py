"""Dependency wiring. One process-wide ``TraceService`` over the in-memory store.

Swapping in a Postgres store later is a change to ``_build_service`` only.
"""

from __future__ import annotations

from functools import lru_cache

from app.domain.service import TraceService
from app.domain.store import InMemoryInvestigationStore


@lru_cache
def get_trace_service() -> TraceService:
    return TraceService(InMemoryInvestigationStore())
