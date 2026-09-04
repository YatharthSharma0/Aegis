"""Case-management endpoints (``05-API-Contracts`` §Case management)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import (
    CurrentUser,
    audit_actor_of,
    get_audit_service,
    get_case_service,
    get_current_user,
    get_trace_service,
)
from app.api.middleware import get_request_id
from app.domain.audit import AuditService
from app.domain.cases import CaseService, CaseStatus, CaseUpdate, ComplaintSource
from app.domain.service import TraceService

router = APIRouter(
    prefix="/api/v1/cases", tags=["cases"], dependencies=[Depends(get_current_user)]
)

_Cases = Annotated[CaseService, Depends(get_case_service)]
_Traces = Annotated[TraceService, Depends(get_trace_service)]
_Audit = Annotated[AuditService, Depends(get_audit_service)]
_RequestId = Annotated[str, Depends(get_request_id)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateCaseRequest(_Model):
    ref_no: str = Field(min_length=1)
    title: str = Field(min_length=1)
    typology_hint: str | None = None
    notes: str | None = None


class UpdateCaseRequest(_Model):
    title: str | None = None
    status: CaseStatus | None = None
    typology_hint: str | None = None
    notes: str | None = None


class AddComplaintRequest(_Model):
    source: ComplaintSource = ComplaintSource.MANUAL
    text: str = Field(min_length=1)
    is_demo: bool = True


class CaseOut(_Model):
    id: str
    ref_no: str
    title: str
    status: str
    typology_hint: str | None
    notes: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class ComplaintOut(_Model):
    id: str
    source: str
    is_demo: bool
    received_at: datetime
    text_preview: str


class TraceRunSummary(_Model):
    trace_id: str
    status: str
    start_address: str
    created_at: datetime
    result_hash: str | None


class CaseDetailOut(CaseOut):
    complaints: list[ComplaintOut]
    trace_runs: list[TraceRunSummary]


def _case_out(case) -> CaseOut:  # type: ignore[no-untyped-def]
    return CaseOut(
        id=case.id, ref_no=case.ref_no, title=case.title, status=case.status.value,
        typology_hint=case.typology_hint, notes=case.notes, created_by=case.created_by,
        created_at=case.created_at, updated_at=case.updated_at,
    )


@router.post("", status_code=201, response_model=CaseOut)
def create_case(
    request: CreateCaseRequest,
    cases: _Cases,
    audit: _Audit,
    user: CurrentUser,
    request_id: _RequestId,
) -> CaseOut:
    case = cases.create(
        ref_no=request.ref_no,
        title=request.title,
        created_by=user.id,
        typology_hint=request.typology_hint,
        notes=request.notes,
    )
    audit.record(
        "case.create", actor=audit_actor_of(user), case_id=case.id,
        detail={"ref_no": case.ref_no}, request_id=request_id,
    )
    return _case_out(case)


@router.get("", response_model=list[CaseOut])
def list_cases(
    cases: _Cases,
    user: CurrentUser,
    status: CaseStatus | None = None,
    mine: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[CaseOut]:
    created_by = user.id if mine else None
    return [
        _case_out(c) for c in cases.search(status=status, created_by=created_by, limit=limit)
    ]


@router.get("/{case_id}", response_model=CaseDetailOut)
def get_case(case_id: str, cases: _Cases, traces: _Traces) -> CaseDetailOut:
    case = cases.get(case_id)
    complaints = [
        ComplaintOut(
            id=c.id, source=c.source.value, is_demo=c.is_demo, received_at=c.received_at,
            text_preview=c.raw_text[:160],
        )
        for c in cases.complaints(case_id)
    ]
    runs = [
        TraceRunSummary(
            trace_id=r.trace_id, status=r.status.value, start_address=r.start_address,
            created_at=r.created_at,
            result_hash=r.investigation.result_hash() if r.investigation else None,
        )
        for r in traces.store.list_by_case(case_id)
    ]
    base = _case_out(case).model_dump()
    return CaseDetailOut(**base, complaints=complaints, trace_runs=runs)


@router.patch("/{case_id}", response_model=CaseOut)
def update_case(  # noqa: PLR0913, PLR0917
    case_id: str,
    request: UpdateCaseRequest,
    cases: _Cases,
    audit: _Audit,
    user: CurrentUser,
    request_id: _RequestId,
) -> CaseOut:
    case = cases.update(
        case_id,
        CaseUpdate(
            title=request.title,
            status=request.status,
            typology_hint=request.typology_hint,
            notes=request.notes,
        ),
    )
    audit.record(
        "case.update", actor=audit_actor_of(user), case_id=case_id,
        detail={"status": case.status.value}, request_id=request_id,
    )
    return _case_out(case)


@router.post("/{case_id}/complaints", status_code=201, response_model=ComplaintOut)
def add_complaint(  # noqa: PLR0913, PLR0917
    case_id: str,
    request: AddComplaintRequest,
    cases: _Cases,
    audit: _Audit,
    user: CurrentUser,
    request_id: _RequestId,
) -> ComplaintOut:
    complaint = cases.attach_complaint(
        case_id, source=request.source, text=request.text, is_demo=request.is_demo
    )
    audit.record(
        "complaint.attach", actor=audit_actor_of(user), case_id=case_id,
        detail={"source": complaint.source.value}, request_id=request_id,
    )
    return ComplaintOut(
        id=complaint.id, source=complaint.source.value, is_demo=complaint.is_demo,
        received_at=complaint.received_at, text_preview=complaint.raw_text[:160],
    )
