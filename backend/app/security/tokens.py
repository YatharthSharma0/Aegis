"""JWT encode/decode for access and refresh tokens.

Access tokens carry ``sub`` (user id) + ``role``; refresh tokens carry ``sub`` +
``jti`` (so they can be individually revoked). Both carry ``type`` so one cannot
be used where the other is expected.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt

from app.config import get_settings

TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    """A token was missing, malformed, expired, or the wrong type."""


@dataclass(frozen=True)
class AccessClaims:
    user_id: str
    role: str


@dataclass(frozen=True)
class RefreshClaims:
    user_id: str
    jti: str


def _now() -> datetime:
    return datetime.now(UTC)


def _encode(payload: dict[str, Any], ttl_s: int) -> str:
    settings = get_settings()
    issued = _now()
    body = {
        **payload,
        "iat": int(issued.timestamp()),
        "exp": int((issued + timedelta(seconds=ttl_s)).timestamp()),
    }
    return jwt.encode(body, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        claims: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if claims.get("type") != expected_type:
        raise TokenError(f"expected a {expected_type} token")
    return claims


def create_access_token(user_id: str, role: str) -> str:
    return _encode(
        {"sub": user_id, "role": role, "type": "access", "jti": uuid.uuid4().hex},
        get_settings().access_token_ttl_s,
    )


def create_refresh_token(user_id: str, *, jti: str | None = None) -> tuple[str, str]:
    """Return ``(token, jti)``. Store the jti to allow revocation."""
    token_jti = jti or uuid.uuid4().hex
    token = _encode({"sub": user_id, "jti": token_jti, "type": "refresh"},
                    get_settings().refresh_token_ttl_s)
    return token, token_jti


def decode_access_token(token: str) -> AccessClaims:
    claims = _decode(token, "access")
    if "sub" not in claims or "role" not in claims:
        raise TokenError("access token missing sub/role")
    return AccessClaims(user_id=str(claims["sub"]), role=str(claims["role"]))


def decode_refresh_token(token: str) -> RefreshClaims:
    claims = _decode(token, "refresh")
    if "sub" not in claims or "jti" not in claims:
        raise TokenError("refresh token missing sub/jti")
    return RefreshClaims(user_id=str(claims["sub"]), jti=str(claims["jti"]))
