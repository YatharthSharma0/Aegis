"""Aegis backend entrypoint.

Exposes the health check and the Phase 2 trace API (``/api/v1/trace``). The
trace runs the Phase 1 engine on a background task (single-process demo
fallback); persistence, a durable worker, auth, and the audit log land in
later Phase 2 PRs.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.routes_auth import router as auth_router
from app.api.routes_trace import router as trace_router
from app.config import get_settings
from app.db.engine import create_all

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Production runs Alembic migrations via the container entrypoint; elsewhere
    # create tables directly so `uvicorn app.main:app` just works.
    if settings.environment != "production":
        create_all()
    yield


app = FastAPI(
    title="Aegis API",
    version=__version__,
    summary="Real-time crypto fraud attribution (SIH26183)",
    lifespan=lifespan,
)

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
