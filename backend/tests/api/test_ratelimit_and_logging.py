"""Rate limiting on trace-start / login, and structured logging."""

import io
import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.api.ratelimit import RateLimiter, get_rate_limiter
from app.config import get_settings
from app.domain.errors import RateLimitedError
from app.logging import _JsonFormatter, _RequestIdFilter, request_id_ctx

SEED = "TK2Weg3fYewPVRw9vA8AbxFpZhcemD6dyC"


# --- RateLimiter unit -------------------------------------------------


def test_limiter_allows_up_to_limit_then_blocks():
    clock = {"t": 1_000_000.0}
    limiter = RateLimiter(clock=lambda: clock["t"])
    for _ in range(3):
        limiter.check("s", "k", limit=3)
    with pytest.raises(RateLimitedError) as exc:
        limiter.check("s", "k", limit=3)
    assert exc.value.retry_after_s > 0


def test_limiter_window_rolls_over():
    clock = {"t": 1_000_000.0}
    limiter = RateLimiter(clock=lambda: clock["t"])
    limiter.check("s", "k", limit=1)
    with pytest.raises(RateLimitedError):
        limiter.check("s", "k", limit=1)
    clock["t"] += 61  # next minute
    limiter.check("s", "k", limit=1)  # allowed again


def test_limit_zero_disables():
    RateLimiter().check("s", "k", limit=0)  # no raise


# --- HTTP -----------------------------------------------------------


@pytest.fixture
def low_trace_limit(monkeypatch):
    monkeypatch.setenv("AEGIS_TRACE_RATE_PER_MIN", "3")
    get_settings.cache_clear()
    get_rate_limiter().reset()
    yield
    get_settings.cache_clear()


def test_trace_start_is_rate_limited(client: TestClient, officer_headers, low_trace_limit):
    for _ in range(3):
        assert client.post(
            "/api/v1/trace", json={"address": SEED}, headers=officer_headers
        ).status_code == 202
    blocked = client.post("/api/v1/trace", json={"address": SEED}, headers=officer_headers)
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert int(blocked.headers["Retry-After"]) > 0


def test_login_is_rate_limited(client: TestClient, monkeypatch):
    monkeypatch.setenv("AEGIS_LOGIN_RATE_PER_MIN", "2")
    get_settings.cache_clear()
    get_rate_limiter().reset()
    try:
        for _ in range(2):
            client.post("/api/v1/auth/login", json={"email": "x@y.z", "password": "nope1234"})
        blocked = client.post(
            "/api/v1/auth/login", json={"email": "x@y.z", "password": "nope1234"}
        )
        assert blocked.status_code == 429
    finally:
        get_settings.cache_clear()


# --- logging ------------------------------------------------------


def test_json_formatter_emits_request_id_and_extras():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(_RequestIdFilter())
    handler.setFormatter(_JsonFormatter())
    logger = logging.getLogger("aegis.test.json")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    token = request_id_ctx.set("req-abc-123")
    try:
        logger.info("hello", extra={"k": "v"})
    finally:
        request_id_ctx.reset(token)
        logger.removeHandler(handler)

    record = json.loads(stream.getvalue().strip())
    assert record["msg"] == "hello"
    assert record["request_id"] == "req-abc-123"
    assert record["k"] == "v"
    assert record["level"] == "INFO"


def test_access_line_is_emitted_per_request(client: TestClient, caplog):
    with caplog.at_level(logging.INFO, logger="aegis.access"):
        client.get("/api/v1/health")
    assert any("/api/v1/health -> 200" in r.message for r in caplog.records)
