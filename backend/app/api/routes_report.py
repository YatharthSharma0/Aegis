"""Report + SAHYOG notice endpoints (``05-API-Contracts`` §Trace)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import (
    CurrentUser,
    audit_actor_of,
    get_audit_service,
    get_current_user,
    get_trace_service,
)
from app.api.middleware import get_request_id
from app.domain.audit import AuditService
from app.domain.errors import InvalidRequestError
from app.domain.reports import build_report, build_sahyog_notice
from app.domain.service import TraceService

router = APIRouter(
    prefix="/api/v1/trace", tags=["report"], dependencies=[Depends(get_current_user)]
)

_Service = Annotated[TraceService, Depends(get_trace_service)]
_Audit = Annotated[AuditService, Depends(get_audit_service)]
_RequestId = Annotated[str, Depends(get_request_id)]


class SahyogNoticeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vasp_rank: int = Field(default=1, ge=1)
    requesting_officer: str | None = None
    case_ref: str | None = None
    legal_basis: str | None = None


@router.get("/{trace_id}/report")
def get_report(  # noqa: PLR0913, PLR0917
    trace_id: str,
    service: _Service,
    audit: _Audit,
    user: CurrentUser,
    request_id: _RequestId,
    fmt: Annotated[Literal["json", "pdf"], Query(alias="format")] = "json",
) -> dict[str, Any]:
    if fmt == "pdf":
        raise InvalidRequestError(
            "PDF rendering is not implemented yet; request format=json"
        )
    record = service.get(trace_id)
    report = build_report(record, generated_by=user.email)
    audit.record(
        "report.generate",
        actor=audit_actor_of(user),
        trace_id=trace_id,
        result_hash=report["header"]["result_hash"],
        detail={"format": fmt},
        request_id=request_id,
    )
    return report


@router.post("/{trace_id}/sahyog-notice")
def create_sahyog_notice(  # noqa: PLR0913, PLR0917
    trace_id: str,
    request: SahyogNoticeRequest,
    service: _Service,
    audit: _Audit,
    user: CurrentUser,
    request_id: _RequestId,
) -> dict[str, Any]:
    record = service.get(trace_id)
    draft = build_sahyog_notice(
        record,
        vasp_rank=request.vasp_rank,
        requesting_officer=request.requesting_officer,
        case_ref=request.case_ref,
        legal_basis=request.legal_basis,
    )
    audit.record(
        "notice.draft",
        actor=audit_actor_of(user),
        trace_id=trace_id,
        detail={"vasp_rank": request.vasp_rank},
        request_id=request_id,
    )
    return draft
