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


class InvalidTraceRequestError(DomainError):
    status = 400
    code = "invalid_request"


class TraceNotFoundError(DomainError):
    status = 404
    code = "not_found"

    def __init__(self, trace_id: str) -> None:
        super().__init__(f"no trace with id {trace_id!r}", details={"trace_id": trace_id})


class TraceNotReadyError(DomainError):
    status = 409
    code = "trace_not_ready"

    def __init__(self, trace_id: str, status: str) -> None:
        super().__init__(
            f"trace {trace_id!r} is {status}, not finished",
            details={"trace_id": trace_id, "status": status},
        )
