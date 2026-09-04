"""Investigation storage.

``InvestigationStore`` is the seam the rest of the backend depends on. Phase 2
ships :class:`InMemoryInvestigationStore`; a Postgres-backed implementation lands
later behind the same three methods without touching :mod:`app.domain.service`.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.engine.records import Chain
from app.engine.result import Investigation, TraceParams, TraceStatus


@dataclass
class InvestigationRecord:
    """One trace run and everything known about it so far."""

    trace_id: str
    case_id: str | None
    start_address: str
    chain: Chain
    params: TraceParams
    status: TraceStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    investigation: Investigation | None = None
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


class InvestigationStore(Protocol):
    def create(self, record: InvestigationRecord) -> None: ...
    def get(self, trace_id: str) -> InvestigationRecord | None: ...
    def update(self, record: InvestigationRecord) -> None: ...


class InMemoryInvestigationStore:
    """Process-local store. Records survive only as long as the process."""

    def __init__(self) -> None:
        self._records: dict[str, InvestigationRecord] = {}
        self._lock = threading.Lock()

    def create(self, record: InvestigationRecord) -> None:
        with self._lock:
            if record.trace_id in self._records:
                raise KeyError(f"trace {record.trace_id} already exists")
            self._records[record.trace_id] = record

    def get(self, trace_id: str) -> InvestigationRecord | None:
        with self._lock:
            return self._records.get(trace_id)

    def update(self, record: InvestigationRecord) -> None:
        with self._lock:
            self._records[record.trace_id] = record
