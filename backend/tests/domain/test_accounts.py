"""AccountService: authenticate, issue, rotate."""

import pytest

from app.domain.account_store import SqlAccountStore
from app.domain.accounts import AccountService, Role
from app.domain.errors import AuthenticationError, InvalidTraceRequestError
from app.security.tokens import decode_access_token


@pytest.fixture
def service() -> AccountService:
    return AccountService(SqlAccountStore())


def _officer(service: AccountService, password: str = "hunter2hunter2"):
    return service.create_user(
        email="Priya@mahacyber.gov.in", full_name="Priya K", role=Role.OFFICER,
        password=password,
    )


def test_create_user_normalises_email(service: AccountService):
    account = _officer(service)
    assert account.email == "priya@mahacyber.gov.in"
    assert account.role is Role.OFFICER


def test_create_user_rejects_short_password(service: AccountService):
    with pytest.raises(InvalidTraceRequestError):
        service.create_user(
            email="x@y.gov", full_name="X", role=Role.ANALYST, password="short",
        )


def test_authenticate_success_is_case_insensitive_on_email(service: AccountService):
    _officer(service)
    account = service.authenticate("PRIYA@mahacyber.gov.in", "hunter2hunter2")
    assert account.role is Role.OFFICER


def test_authenticate_wrong_password_raises(service: AccountService):
    _officer(service)
    with pytest.raises(AuthenticationError):
        service.authenticate("priya@mahacyber.gov.in", "wrong")


def test_authenticate_unknown_email_raises(service: AccountService):
    with pytest.raises(AuthenticationError):
        service.authenticate("nobody@nowhere.gov", "whatever12")


def test_issue_tokens_shape(service: AccountService):
    account = _officer(service)
    pair = service.issue_tokens(account)
    assert decode_access_token(pair.access_token).user_id == account.id
    assert pair.role is Role.OFFICER
    assert pair.expires_in == 900


def test_refresh_rotates_and_burns_the_old_token(service: AccountService):
    account = _officer(service)
    first = service.issue_tokens(account)

    second = service.refresh(first.refresh_token)
    assert second.access_token != first.access_token
    assert second.refresh_token != first.refresh_token

    # the first refresh token is now revoked
    with pytest.raises(AuthenticationError):
        service.refresh(first.refresh_token)
    # the second still works
    assert service.refresh(second.refresh_token)


def test_refresh_rejects_garbage(service: AccountService):
    with pytest.raises(AuthenticationError):
        service.refresh("not.a.jwt")
