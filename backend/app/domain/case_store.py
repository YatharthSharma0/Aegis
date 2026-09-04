"""SQLAlchemy-backed :class:`~app.domain.cases.CaseStore`."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.db.engine import session_scope
from app.db.models import Case as CaseRow
from app.db.models import Complaint as ComplaintRow
from app.domain.cases import Case, CaseStatus, Complaint, ComplaintSource


class SqlCaseStore:
    def create(self, case: Case) -> None:
        with session_scope() as session:
            session.add(_case_row(case))

    def get(self, case_id: str) -> Case | None:
        with session_scope() as session:
            row = session.get(CaseRow, case_id)
            return _to_case(row) if row is not None else None

    def get_by_ref(self, ref_no: str) -> Case | None:
        with session_scope() as session:
            row = session.scalar(select(CaseRow).where(CaseRow.ref_no == ref_no))
            return _to_case(row) if row is not None else None

    def search(
        self, *, status: CaseStatus | None, created_by: str | None, limit: int
    ) -> list[Case]:
        stmt = select(CaseRow).order_by(CaseRow.created_at.desc()).limit(limit)
        if status is not None:
            stmt = stmt.where(CaseRow.status == status.value)
        if created_by is not None:
            stmt = stmt.where(CaseRow.created_by == created_by)
        with session_scope() as session:
            return [_to_case(row) for row in session.scalars(stmt)]

    def save(self, case: Case) -> None:
        with session_scope() as session:
            row = session.get(CaseRow, case.id)
            if row is None:
                session.add(_case_row(case))
                return
            row.title = case.title
            row.status = case.status.value
            row.typology_hint = case.typology_hint
            row.notes = case.notes
            row.updated_at = case.updated_at

    def add_complaint(self, complaint: Complaint) -> None:
        with session_scope() as session:
            session.add(
                ComplaintRow(
                    id=complaint.id,
                    case_id=complaint.case_id,
                    source=complaint.source.value,
                    raw_text=complaint.raw_text,
                    is_demo=complaint.is_demo,
                    extracted=complaint.extracted,
                    received_at=complaint.received_at,
                )
            )

    def complaints_for(self, case_id: str) -> list[Complaint]:
        stmt = (
            select(ComplaintRow)
            .where(ComplaintRow.case_id == case_id)
            .order_by(ComplaintRow.received_at.asc())
        )
        with session_scope() as session:
            return [_to_complaint(row) for row in session.scalars(stmt)]


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _case_row(case: Case) -> CaseRow:
    return CaseRow(
        id=case.id,
        ref_no=case.ref_no,
        title=case.title,
        status=case.status.value,
        typology_hint=case.typology_hint,
        notes=case.notes,
        created_by=case.created_by,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


def _to_case(row: CaseRow) -> Case:
    return Case(
        id=row.id,
        ref_no=row.ref_no,
        title=row.title,
        status=CaseStatus(row.status),
        typology_hint=row.typology_hint,
        notes=row.notes,
        created_by=row.created_by,
        created_at=_aware(row.created_at),
        updated_at=_aware(row.updated_at),
    )


def _to_complaint(row: ComplaintRow) -> Complaint:
    return Complaint(
        id=row.id,
        case_id=row.case_id,
        source=ComplaintSource(row.source),
        raw_text=row.raw_text,
        is_demo=row.is_demo,
        extracted=row.extracted,
        received_at=_aware(row.received_at),
    )
