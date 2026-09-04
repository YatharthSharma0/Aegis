"""Aegis backend entrypoint.

Phase 0: a minimal FastAPI application exposing a health check. The tracing
engine, persistence, workers, and AI components are added in later phases per
the execution plan.
"""

from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import __version__
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Aegis API",
    version=__version__,
    summary="Real-time crypto fraud attribution (SIH26183)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    """Payload returned by the health check."""

    status: Literal["ok"]
    service: str
    version: str
    environment: str


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """Report that the service is up. Used by CI, Compose, and uptime checks."""
    return HealthResponse(
        status="ok",
        service="aegis-backend",
        version=__version__,
        environment=settings.environment,
    )
