"""Per-request id + an access log line.

Read ``X-Request-ID`` or mint one; stash it on ``request.state``, bind it to the
logging context var, echo it in the response, and log one structured line per
request. Audit rows also record the id, so everything ties together.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logging import request_id_ctx

REQUEST_ID_HEADER = "X-Request-ID"
_access = logging.getLogger("aegis.access")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            _access.info(
                "%s %s -> %s",
                request.method,
                request.url.path,
                response.status_code,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
        finally:
            request_id_ctx.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")
