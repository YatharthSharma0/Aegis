"""Trace endpoints (``05-API-Contracts`` §Trace).

Phase 2 P1: ``POST /trace`` queues a run and a background task executes it;
``GET /trace/{id}`` is the authoritative status/result path (polling first).
The background task is FastAPI ``BackgroundTasks`` — the labelled single-process
demo fallback; a durable Redis-backed worker replaces it in a later PR.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.deps import get_trace_service
from app.domain.schemas import (
    TraceAccepted,
    TraceGraphResponse,
    TraceRequest,
    TraceStatusResponse,
)
from app.domain.service import TraceService

router = APIRouter(prefix="/api/v1", tags=["trace"])

_Service = Annotated[TraceService, Depends(get_trace_service)]


@router.post("/trace", status_code=202, response_model=TraceAccepted)
def start_trace(
    request: TraceRequest, background: BackgroundTasks, service: _Service
) -> TraceAccepted:
    record = service.start_trace(request)
    background.add_task(service.run_trace, record.trace_id)
    return TraceAccepted(
        trace_id=record.trace_id,
        status=record.status,
        stream_url=f"/api/v1/trace/{record.trace_id}/stream",
    )


@router.get("/trace/{trace_id}", response_model=TraceStatusResponse)
def get_trace(trace_id: str, service: _Service) -> TraceStatusResponse:
    return TraceStatusResponse.of(service.get(trace_id))


@router.get("/trace/{trace_id}/graph", response_model=TraceGraphResponse)
def get_trace_graph(trace_id: str, service: _Service) -> TraceGraphResponse:
    return TraceGraphResponse.of(service.get(trace_id))
