"""User accounts and the auth flow: authenticate, issue tokens, rotate refresh.

Transport-free. The HTTP layer turns these into ``/auth/login`` /
``/auth/refresh`` and the ``current_user`` dependency.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

from app.config import get_settings
from app.domain.errors import AuthenticationError, InvalidTraceRequestError
from app.security.passwords import hash_password, verify_password
from app.security.tokens import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)


class Role(StrEnum):
    OFFICER = "officer"
    ANALYST = "analyst"
    ADMIN = "admin"


@dataclass(frozen=True)
class Account:
    id: str
    email: str
    full_name: str
    role: Role
    unit: str | None
    is_active: bool


@dataclass(frozen=True)
class Credentials:
    """An account plus its stored password hash, as returned by the store."""

    account: Account
    password_hash: str


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    role: Role
    expires_in: int


class AccountStore(Protocol):
    def get_credentials_by_email(self, email: str) -> Credentials | None: ...
    def get_by_id(self, user_id: str) -> Account | None: ...
    def create(self, account: Account, password_hash: str) -> None: ...
    def record_refresh(self, jti: str, user_id: str, expires_at: datetime) -> None: ...
    def refresh_is_active(self, jti: str, user_id: str) -> bool: ...
    def revoke_refresh(self, jti: str) -> None: ...


class AccountService:
    def __init__(self, store: AccountStore) -> None:
        self._store = store

    # -- registration (CLI / admin only; no public signup) ----------------

    def create_user(
        self, *, email: str, full_name: str, role: Role, password: str, unit: str | None = None
    ) -> Account:
        email = email.strip().lower()
        if not email or "@" not in email:
            raise InvalidTraceRequestError(f"invalid email: {email!r}")
        if len(password) < 8:
            raise InvalidTraceRequestError("password must be at least 8 characters")
        account = Account(
            id=uuid.uuid4().hex,
            email=email,
            full_name=full_name,
            role=role,
            unit=unit,
            is_active=True,
        )
        self._store.create(account, hash_password(password))
        return account

    # -- auth ----------------------------------------------------------

    def authenticate(self, email: str, password: str) -> Account:
        creds = self._store.get_credentials_by_email(email.strip().lower())
        # Verify even on a miss to keep timing uniform.
        placeholder = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdHNhbHQ$0000000000000000000000000000"
        if creds is None:
            verify_password(password, placeholder)
            raise AuthenticationError("invalid email or password")
        if not verify_password(password, creds.password_hash) or not creds.account.is_active:
            raise AuthenticationError("invalid email or password")
        return creds.account

    def issue_tokens(self, account: Account) -> TokenPair:
        settings = get_settings()
        access = create_access_token(account.id, account.role.value)
        refresh, jti = create_refresh_token(account.id)
        expires_at = datetime.now(UTC) + timedelta(seconds=settings.refresh_token_ttl_s)
        self._store.record_refresh(jti, account.id, expires_at)
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            role=account.role,
            expires_in=settings.access_token_ttl_s,
        )

    def refresh(self, refresh_token: str) -> TokenPair:
        try:
            claims = decode_refresh_token(refresh_token)
        except TokenError as exc:
            raise AuthenticationError(str(exc)) from exc
        if not self._store.refresh_is_active(claims.jti, claims.user_id):
            raise AuthenticationError("refresh token is revoked or unknown")
        account = self._store.get_by_id(claims.user_id)
        if account is None or not account.is_active:
            raise AuthenticationError("account is inactive")
        # Rotation: burn the presented token, issue a fresh pair.
        self._store.revoke_refresh(claims.jti)
        return self.issue_tokens(account)

    def get(self, user_id: str) -> Account | None:
        return self._store.get_by_id(user_id)
