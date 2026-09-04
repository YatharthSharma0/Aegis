"""Investigation storage + the durable-queue claim.

``InvestigationStore`` is the seam the rest of the backend depends on. Two
implementations: :class:`InMemoryInvestigationStore` (unit tests) and
``SqlInvestigationStore`` (real). ``claim_next`` is what makes trace execution
durable — a worker atomically moves the oldest ``queued`` (or lease-expired
``running``) row to ``running`` with a fresh lease.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
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
    attempts: int = 0
    worker_id: str | None = None
    lease_expires_at: datetime | None = None
    investigation: Investigation | None = None
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


class InvestigationStore(Protocol):
    def create(self, record: InvestigationRecord) -> None: ...
    def get(self, trace_id: str) -> InvestigationRecord | None: ...
    def update(self, record: InvestigationRecord) -> None: ...
    def list_by_case(self, case_id: str) -> list[InvestigationRecord]: ...
    def claim_next(self, worker_id: str, lease_s: float) -> InvestigationRecord | None:
        """Atomically claim the next runnable trace, or return ``None``."""
        ...


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

    def list_by_case(self, case_id: str) -> list[InvestigationRecord]:
        with self._lock:
            return sorted(
                (r for r in self._records.values() if r.case_id == case_id),
                key=lambda r: r.created_at,
            )

    def claim_next(self, worker_id: str, lease_s: float) -> InvestigationRecord | None:
        now = datetime.now(UTC)
        with self._lock:
            runnable = [
                r
                for r in self._records.values()
                if r.status is TraceStatus.QUEUED
                or (
                    r.status is TraceStatus.RUNNING
                    and r.lease_expires_at is not None
                    and r.lease_expires_at <= now
                )
            ]
            if not runnable:
                return None
            record = min(runnable, key=lambda r: r.created_at)
            record.status = TraceStatus.RUNNING
            record.worker_id = worker_id
            record.attempts += 1
            record.started_at = record.started_at or now
            record.lease_expires_at = now + timedelta(seconds=lease_s)
            return record
