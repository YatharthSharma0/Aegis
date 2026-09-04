"""CaseService: create, uniqueness, update, complaint rules."""

import pytest

from app.domain.case_store import SqlCaseStore
from app.domain.cases import CaseService, CaseStatus, CaseUpdate, ComplaintSource
from app.domain.errors import CaseNotFoundError, ConflictError, InvalidRequestError


@pytest.fixture
def service() -> CaseService:
    return CaseService(SqlCaseStore())


def test_create_and_get(service: CaseService):
    case = service.create(ref_no="FIR 0142/2026", title="Task scam", created_by="u1")
    assert case.status is CaseStatus.OPEN
    assert service.get(case.id).ref_no == "FIR 0142/2026"


def test_ref_no_must_be_unique(service: CaseService):
    service.create(ref_no="FIR-1", title="A", created_by="u1")
    with pytest.raises(ConflictError):
        service.create(ref_no="FIR-1", title="B", created_by="u2")


def test_get_missing_raises(service: CaseService):
    with pytest.raises(CaseNotFoundError):
        service.get("nope")


def test_update_changes_status_and_bumps_updated_at(service: CaseService):
    case = service.create(ref_no="FIR-2", title="A", created_by="u1")
    updated = service.update(case.id, CaseUpdate(status=CaseStatus.CLOSED, notes="done"))
    assert updated.status is CaseStatus.CLOSED
    assert updated.notes == "done"
    assert updated.updated_at >= case.updated_at
    assert updated.ref_no == case.ref_no  # immutable


def test_attach_demo_complaint(service: CaseService):
    case = service.create(ref_no="FIR-3", title="A", created_by="u1")
    c = service.attach_complaint(
        case.id, source=ComplaintSource.NCRP, text="fake narrative", is_demo=True
    )
    assert c.is_demo is True
    assert [x.id for x in service.complaints(case.id)] == [c.id]


def test_real_complaint_is_refused(service: CaseService):
    case = service.create(ref_no="FIR-4", title="A", created_by="u1")
    with pytest.raises(InvalidRequestError, match="encryption"):
        service.attach_complaint(
            case.id, source=ComplaintSource.MANUAL, text="real PII", is_demo=False
        )
