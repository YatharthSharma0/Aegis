"""SQLAlchemy-backed :class:`~app.domain.accounts.AccountStore`."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.db.engine import session_scope
from app.db.models import RefreshToken, User
from app.domain.accounts import Account, Credentials, Role


class SqlAccountStore:
    def get_credentials_by_email(self, email: str) -> Credentials | None:
        with session_scope() as session:
            row = session.scalar(select(User).where(User.email == email))
            return _to_credentials(row) if row is not None else None

    def get_by_id(self, user_id: str) -> Account | None:
        with session_scope() as session:
            row = session.get(User, user_id)
            return _to_account(row) if row is not None else None

    def create(self, account: Account, password_hash: str) -> None:
        with session_scope() as session:
            session.add(
                User(
                    id=account.id,
                    email=account.email,
                    full_name=account.full_name,
                    role=account.role.value,
                    unit=account.unit,
                    password_hash=password_hash,
                    is_active=account.is_active,
                    created_at=datetime.now(UTC),
                )
            )

    def record_refresh(self, jti: str, user_id: str, expires_at: datetime) -> None:
        with session_scope() as session:
            session.add(
                RefreshToken(
                    jti=jti,
                    user_id=user_id,
                    expires_at=expires_at,
                    revoked=False,
                    created_at=datetime.now(UTC),
                )
            )

    def refresh_is_active(self, jti: str, user_id: str) -> bool:
        with session_scope() as session:
            row = session.get(RefreshToken, jti)
            if row is None or row.revoked or row.user_id != user_id:
                return False
            return _aware(row.expires_at) > datetime.now(UTC)

    def revoke_refresh(self, jti: str) -> None:
        with session_scope() as session:
            row = session.get(RefreshToken, jti)
            if row is not None:
                row.revoked = True


def _aware(value: datetime) -> datetime:
    # SQLite hands back naive datetimes even for timezone=True columns.
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _to_account(row: User) -> Account:
    return Account(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        role=Role(row.role),
        unit=row.unit,
        is_active=row.is_active,
    )


def _to_credentials(row: User) -> Credentials:
    return Credentials(account=_to_account(row), password_hash=row.password_hash)
