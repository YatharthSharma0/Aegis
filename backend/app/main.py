"""Aegis backend entrypoint.

Exposes the health check, auth, the trace API (``/api/v1/trace``) and the admin
audit endpoint. Traces execute on the durable worker: in-process
(``AEGIS_TRACE_WORKER=inline``, default) or a separate ``python -m app.worker``.
"""

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.middleware import RequestIdMiddleware
from app.api.routes_admin import router as admin_router
from app.api.routes_auth import router as auth_router
from app.api.routes_cases import router as cases_router
from app.api.routes_report import router as report_router
from app.api.routes_trace import router as trace_router
from app.config import get_settings
from app.db.engine import create_all
from app.domain.audit import AuditService
from app.domain.audit_store import SqlAuditStore
from app.domain.service import TraceService
from app.domain.sql_store import SqlInvestigationStore
from app.logging import configure_logging
from app.worker import TraceWorker

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(json_output=settings.log_json, level=settings.log_level)
    # Production runs Alembic migrations via the container entrypoint; elsewhere
    # create tables directly so `uvicorn app.main:app` just works.
    if settings.environment != "production":
        create_all()

    stop = threading.Event()
    thread: threading.Thread | None = None
    if settings.trace_worker == "inline":
        worker = TraceWorker(
            TraceService(SqlInvestigationStore()),
            AuditService(SqlAuditStore()),
            lease_s=settings.worker_lease_s,
            max_attempts=settings.worker_max_attempts,
            poll_s=settings.worker_poll_s,
        )
        thread = threading.Thread(
            target=worker.run_forever, args=(stop,), name="trace-worker", daemon=True
        )
        thread.start()
    try:
        yield
    finally:
        stop.set()
        if thread is not None:
            thread.join(timeout=5)


app = FastAPI(
    title="Aegis API",
    version=__version__,
    summary="Real-time crypto fraud attribution (SIH26183)",
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(trace_router)
app.include_router(cases_router)
app.include_router(report_router)
app.include_router(admin_router)


class HealthResponse(BaseModel):
    """Payload returned by the health check."""

    status: Literal["ok"]
    service: str
    version: str
    environment: str


@app.get("/health", response_model=HealthResponse, tags=["meta"])
@app.get("/api/v1/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """Report that the service is up. Used by CI, Compose, and uptime checks."""
    return HealthResponse(
        status="ok",
        service="aegis-backend",
        version=__version__,
        environment=settings.environment,
    )
