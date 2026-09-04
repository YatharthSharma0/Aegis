"""JWT encode/decode."""

import time

import jwt
import pytest

from app.config import get_settings
from app.security.tokens import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)


def test_access_token_roundtrip():
    token = create_access_token("user-1", "officer")
    claims = decode_access_token(token)
    assert claims.user_id == "user-1"
    assert claims.role == "officer"


def test_refresh_token_roundtrip_carries_jti():
    token, jti = create_refresh_token("user-1")
    claims = decode_refresh_token(token)
    assert claims.user_id == "user-1"
    assert claims.jti == jti


def test_access_token_is_not_accepted_as_a_refresh_token():
    token = create_access_token("user-1", "admin")
    with pytest.raises(TokenError):
        decode_refresh_token(token)


def test_tampered_token_is_rejected():
    token = create_access_token("user-1", "officer")
    with pytest.raises(TokenError):
        decode_access_token(token + "x")


def test_expired_token_is_rejected(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("AEGIS_ACCESS_TOKEN_TTL_S", "1")
    token = create_access_token("user-1", "officer")
    time.sleep(1.2)
    with pytest.raises(TokenError):
        decode_access_token(token)
    get_settings.cache_clear()


def test_wrong_secret_is_rejected():
    token = create_access_token("user-1", "officer")
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(token, "some-other-secret", algorithms=["HS256"])
