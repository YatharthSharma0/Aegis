"""In-process fixed-window rate limiting.

One counter per ``(scope, key)`` per wall-clock minute. Simple and good enough
for a single instance; a multi-instance deployment needs a shared store. Keyed by
user id for authenticated endpoints, by client IP for login.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from app.api.deps import CurrentUser
from app.config import get_settings
from app.domain.errors import RateLimitedError


class RateLimiter:
    def __init__(self, *, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, str, int], int] = {}

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()

    def check(self, scope: str, key: str, limit: int) -> None:
        if limit <= 0:
            return
        now = self._clock()
        window = int(now // 60)
        bucket = (scope, key, window)
        with self._lock:
            # opportunistic cleanup of stale windows
            if len(self._counters) > 4096:
                self._counters = {
                    k: v for k, v in self._counters.items() if k[2] >= window
                }
            count = self._counters.get(bucket, 0) + 1
            self._counters[bucket] = count
        if count > limit:
            raise RateLimitedError(60 - int(now % 60), scope=scope)


@lru_cache
def get_rate_limiter() -> RateLimiter:
    return RateLimiter()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_trace(
    user: CurrentUser,
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> None:
    limiter.check("trace", user.id, get_settings().trace_rate_per_min)


def rate_limit_login(
    request: Request,
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> None:
    limiter.check("login", _client_ip(request), get_settings().login_rate_per_min)
