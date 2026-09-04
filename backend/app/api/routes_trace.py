"""Trace endpoints (``05-API-Contracts`` §Trace).

Phase 2 P1: ``POST /trace`` queues a run and a background task executes it;
``GET /trace/{id}`` is the authoritative status/result path (polling first).
The background task is FastAPI ``BackgroundTasks`` — the labelled single-process
demo fallback; a durable worker replaces it in a later PR.

Every request that touches a trace is written to the hash-chained audit log:
``trace.start`` / ``trace.complete`` / ``trace.failed`` for the lifecycle,
``trace.read`` / ``trace.read_graph`` for evidentiary reads.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.deps import (
    CurrentUser,
    audit_actor_of,
    get_audit_service,
    get_current_user,
    get_trace_service,
)
from app.api.middleware import get_request_id
from app.domain.audit import AuditActor, AuditService
from app.domain.schemas import (
    TraceAccepted,
    TraceGraphResponse,
    TraceRequest,
    TraceStatusResponse,
)
from app.domain.service import TraceService
from app.engine.result import TraceStatus

# Every route on this router requires a valid access token.
router = APIRouter(prefix="/api/v1", tags=["trace"], dependencies=[Depends(get_current_user)])

_Service = Annotated[TraceService, Depends(get_trace_service)]
_Audit = Annotated[AuditService, Depends(get_audit_service)]
_RequestId = Annotated[str, Depends(get_request_id)]


def _run_trace_with_audit(
    service: TraceService, audit: AuditService, trace_id: str, actor: AuditActor,
    request_id: str,
) -> None:
    service.run_trace(trace_id)
    record = service.get(trace_id)
    action = "trace.complete" if record.status is not TraceStatus.FAILED else "trace.failed"
    audit.record(
        action,
        actor=actor,
        trace_id=trace_id,
        result_hash=record.investigation.result_hash() if record.investigation else None,
        detail={"status": record.status.value, "error": record.error},
        request_id=request_id,
    )


@router.post("/trace", status_code=202, response_model=TraceAccepted)
def start_trace(  # noqa: PLR0913, PLR0917 — FastAPI dependency parameters
    request: TraceRequest,
    background: BackgroundTasks,
    service: _Service,
    audit: _Audit,
    user: CurrentUser,
    request_id: _RequestId,
) -> TraceAccepted:
    record = service.start_trace(request)
    actor = audit_actor_of(user)
    audit.record(
        "trace.start",
        actor=actor,
        trace_id=record.trace_id,
        case_id=record.case_id,
        address=record.start_address,
        chain=record.chain.value,
        detail={"params": record.params.model_dump(mode="json")},
        request_id=request_id,
    )
    background.add_task(
        _run_trace_with_audit, service, audit, record.trace_id, actor, request_id
    )
    return TraceAccepted(
        trace_id=record.trace_id,
        status=record.status,
        stream_url=f"/api/v1/trace/{record.trace_id}/stream",
    )


@router.get("/trace/{trace_id}", response_model=TraceStatusResponse)
def get_trace(
    trace_id: str, service: _Service, audit: _Audit, user: CurrentUser, request_id: _RequestId
) -> TraceStatusResponse:
    record = service.get(trace_id)
    audit.record(
        "trace.read", actor=audit_actor_of(user), trace_id=trace_id,
        result_hash=record.investigation.result_hash() if record.investigation else None,
        request_id=request_id,
    )
    return TraceStatusResponse.of(record)


@router.get("/trace/{trace_id}/graph", response_model=TraceGraphResponse)
def get_trace_graph(
    trace_id: str, service: _Service, audit: _Audit, user: CurrentUser, request_id: _RequestId
) -> TraceGraphResponse:
    record = service.get(trace_id)
    audit.record(
        "trace.read_graph", actor=audit_actor_of(user), trace_id=trace_id,
        request_id=request_id,
    )
    return TraceGraphResponse.of(record)
