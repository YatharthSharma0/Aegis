"""Admin endpoints. Requires the ``admin`` role."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import get_audit_service, require_admin
from app.domain.audit import AuditService

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])

_Audit = Annotated[AuditService, Depends(get_audit_service)]


class AuditEntryOut(BaseModel):
    seq: int
    ts: datetime
    actor_id: str | None
    actor_role: str | None
    action: str
    trace_id: str | None
    case_id: str | None
    address: str | None
    chain: str | None
    detail: dict[str, Any] | None
    result_hash: str | None
    request_id: str | None
    prev_row_hash: str
    row_hash: str


class AuditVerificationOut(BaseModel):
    ok: bool
    checked: int
    broken_at_seq: int | None
    reason: str | None


class AuditResponse(BaseModel):
    verification: AuditVerificationOut
    entries: list[AuditEntryOut]


@router.get("/audit", response_model=AuditResponse)
def get_audit(
    audit: _Audit,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    action: str | None = None,
    actor_id: str | None = None,
) -> AuditResponse:
    verification = audit.verify()
    entries = audit.list(limit=limit, action=action, actor_id=actor_id)
    return AuditResponse(
        verification=AuditVerificationOut(
            ok=verification.ok,
            checked=verification.checked,
            broken_at_seq=verification.broken_at_seq,
            reason=verification.reason,
        ),
        entries=[AuditEntryOut(**vars(entry)) for entry in entries],
    )
