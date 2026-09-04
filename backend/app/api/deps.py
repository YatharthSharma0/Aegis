"""Dependency wiring: services + the auth dependencies.

``get_current_user`` decodes the bearer access token and loads the account;
``require_role`` gates a route by role. Public routes (health, login, refresh,
docs) simply don't depend on these.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.account_store import SqlAccountStore
from app.domain.accounts import Account, AccountService, Role
from app.domain.errors import AuthenticationError, AuthorizationError
from app.domain.service import TraceService
from app.domain.sql_store import SqlInvestigationStore
from app.security.tokens import TokenError, decode_access_token


@lru_cache
def get_trace_service() -> TraceService:
    return TraceService(SqlInvestigationStore())


@lru_cache
def get_account_service() -> AccountService:
    return AccountService(SqlAccountStore())


_bearer = HTTPBearer(auto_error=False, description="JWT access token")


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    accounts: Annotated[AccountService, Depends(get_account_service)],
) -> Account:
    if creds is None:
        raise AuthenticationError("missing bearer token")
    try:
        claims = decode_access_token(creds.credentials)
    except TokenError as exc:
        raise AuthenticationError(str(exc)) from exc
    account = accounts.get(claims.user_id)
    if account is None or not account.is_active:
        raise AuthenticationError("account not found or inactive")
    return account


CurrentUser = Annotated[Account, Depends(get_current_user)]


def require_role(*roles: Role) -> Callable[..., Account]:
    def _dependency(user: CurrentUser) -> Account:
        if user.role not in roles:
            allowed = ", ".join(r.value for r in roles)
            raise AuthorizationError(f"requires role: {allowed}")
        return user

    return _dependency


require_admin = require_role(Role.ADMIN)
