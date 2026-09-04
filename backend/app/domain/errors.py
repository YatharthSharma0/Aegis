"""Typed domain errors. Each carries the HTTP status and error code the API
should return, so the transport layer maps them with one handler.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class. ``status`` and ``code`` drive the HTTP response."""

    status: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidRequestError(DomainError):
    status = 400
    code = "invalid_request"


# Back-compat alias — trace code raises this name.
class InvalidTraceRequestError(InvalidRequestError):
    pass


class NotFoundError(DomainError):
    status = 404
    code = "not_found"


class TraceNotFoundError(NotFoundError):
    def __init__(self, trace_id: str) -> None:
        super().__init__(f"no trace with id {trace_id!r}", details={"trace_id": trace_id})


class CaseNotFoundError(NotFoundError):
    def __init__(self, case_id: str) -> None:
        super().__init__(f"no case with id {case_id!r}", details={"case_id": case_id})


class ConflictError(DomainError):
    status = 409
    code = "conflict"


class TraceNotReadyError(DomainError):
    status = 409
    code = "trace_not_ready"

    def __init__(self, trace_id: str, status: str) -> None:
        super().__init__(
            f"trace {trace_id!r} is {status}, not finished",
            details={"trace_id": trace_id, "status": status},
        )


class AuthenticationError(DomainError):
    status = 401
    code = "unauthenticated"


class AuthorizationError(DomainError):
    status = 403
    code = "forbidden"


class RateLimitedError(DomainError):
    status = 429
    code = "rate_limited"

    def __init__(self, retry_after_s: int, *, scope: str) -> None:
        super().__init__(
            f"too many {scope} requests; retry in {retry_after_s}s",
            details={"retry_after_s": retry_after_s, "scope": scope},
        )
        self.retry_after_s = retry_after_s
