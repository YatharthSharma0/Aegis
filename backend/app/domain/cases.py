"""Case management: an investigation folder holding complaints and trace runs.

Transport-free. Real (non-demo) complaint text is refused until application-layer
encryption + a retention policy exist (design vault, DPDP).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from app.domain.errors import CaseNotFoundError, ConflictError, InvalidRequestError


class CaseStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class ComplaintSource(StrEnum):
    NCRP = "ncrp"
    SAHYOG = "sahyog"
    HELPLINE_1930 = "1930"
    MANUAL = "manual"


@dataclass(frozen=True)
class Case:
    id: str
    ref_no: str
    title: str
    status: CaseStatus
    typology_hint: str | None
    notes: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Complaint:
    id: str
    case_id: str
    source: ComplaintSource
    raw_text: str
    is_demo: bool
    extracted: dict[str, Any] | None
    received_at: datetime


@dataclass(frozen=True)
class CaseUpdate:
    title: str | None = None
    status: CaseStatus | None = None
    typology_hint: str | None = None
    notes: str | None = None


class CaseStore(Protocol):
    def create(self, case: Case) -> None: ...
    def get(self, case_id: str) -> Case | None: ...
    def get_by_ref(self, ref_no: str) -> Case | None: ...
    def search(
        self, *, status: CaseStatus | None, created_by: str | None, limit: int
    ) -> list[Case]: ...
    def save(self, case: Case) -> None: ...
    def add_complaint(self, complaint: Complaint) -> None: ...
    def complaints_for(self, case_id: str) -> list[Complaint]: ...


def _now() -> datetime:
    return datetime.now(UTC)


class CaseService:
    def __init__(self, store: CaseStore) -> None:
        self._store = store

    def create(
        self,
        *,
        ref_no: str,
        title: str,
        created_by: str | None,
        typology_hint: str | None = None,
        notes: str | None = None,
    ) -> Case:
        ref_no = ref_no.strip()
        if not ref_no or not title.strip():
            raise InvalidRequestError("ref_no and title are required")
        if self._store.get_by_ref(ref_no) is not None:
            raise ConflictError(f"a case with ref_no {ref_no!r} already exists")
        now = _now()
        case = Case(
            id=uuid.uuid4().hex,
            ref_no=ref_no,
            title=title.strip(),
            status=CaseStatus.OPEN,
            typology_hint=typology_hint,
            notes=notes,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self._store.create(case)
        return case

    def get(self, case_id: str) -> Case:
        case = self._store.get(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)
        return case

    def search(
        self,
        *,
        status: CaseStatus | None = None,
        created_by: str | None = None,
        limit: int = 100,
    ) -> list[Case]:
        return self._store.search(status=status, created_by=created_by, limit=limit)

    def update(self, case_id: str, changes: CaseUpdate) -> Case:
        current = self.get(case_id)
        updated = Case(
            id=current.id,
            ref_no=current.ref_no,
            title=changes.title.strip() if changes.title else current.title,
            status=changes.status or current.status,
            typology_hint=(
                changes.typology_hint
                if changes.typology_hint is not None
                else current.typology_hint
            ),
            notes=changes.notes if changes.notes is not None else current.notes,
            created_by=current.created_by,
            created_at=current.created_at,
            updated_at=_now(),
        )
        self._store.save(updated)
        return updated

    def attach_complaint(
        self, case_id: str, *, source: ComplaintSource, text: str, is_demo: bool
    ) -> Complaint:
        self.get(case_id)  # 404 if missing
        if not is_demo:
            raise InvalidRequestError(
                "real complaint text cannot be stored yet — encryption + retention "
                "policy pending; submit is_demo=true fictional text only"
            )
        if not text.strip():
            raise InvalidRequestError("complaint text is empty")
        complaint = Complaint(
            id=uuid.uuid4().hex,
            case_id=case_id,
            source=source,
            raw_text=text,
            is_demo=True,
            extracted=None,
            received_at=_now(),
        )
        self._store.add_complaint(complaint)
        return complaint

    def complaints(self, case_id: str) -> list[Complaint]:
        self.get(case_id)
        return self._store.complaints_for(case_id)
