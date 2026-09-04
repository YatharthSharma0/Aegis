"""Application configuration, loaded from the environment.

Every configurable value lives here and is documented in ``.env.example``.
Nothing else in the app should read ``os.environ`` directly.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the Aegis backend."""

    model_config = SettingsConfigDict(
        env_prefix="AEGIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    debug: bool = False

    # Comma-separated list of allowed CORS origins (the frontend dev server by default).
    cors_origins: list[str] = ["http://localhost:5173"]

    # --- trace engine wiring -------------------------------------------------
    # fixture: always the recorded synthetic fixture (offline, deterministic).
    # live: always TronGridProvider (requires trongrid_api_key).
    # auto: live iff trongrid_api_key is set and the chain is Tron, else fixture.
    provider_mode: Literal["fixture", "live", "auto"] = "fixture"
    fixture_id: str = "growjoy_tron_trc20"
    # Label packs applied to every trace (attribution). Empty = no attribution.
    label_packs: list[str] = ["aegis_demo_pack"]

    # --- live provider (Phase 4.5) ---------------------------------------
    # TronGrid API key. Never logged, never placed in a ProviderSnapshot's
    # request_params, never in an error message — see docs/PROVIDERS.md.
    trongrid_api_key: str | None = None
    # On-disk response cache (endpoint+params -> raw JSON). None disables
    # caching — every call hits the network. A rehearsal/demo run against the
    # same addresses makes zero live calls once this is warm.
    provider_cache_dir: str | None = "./.provider-cache"

    # --- persistence -------------------------------------------------------
    # SQLAlchemy URL. Local dev default is a file SQLite DB; Compose sets
    # postgresql+psycopg://…. Alembic reads this too.
    database_url: str = "sqlite:///./aegis.db"
    # Log SQL. Never true in production.
    db_echo: bool = False

    # --- trace worker ----------------------------------------------------
    # inline: the API process runs the worker in a background thread (dev).
    # external: a separate `python -m app.worker` process drains the queue.
    trace_worker: Literal["inline", "external"] = "inline"
    worker_lease_s: float = 120.0
    worker_max_attempts: int = 3
    worker_poll_s: float = 1.0

    # --- auth ------------------------------------------------------------
    # HMAC key for signing JWTs. MUST be overridden in production (a startup
    # check refuses to run with this dev default when environment=production).
    jwt_secret: str = "dev-insecure-change-me-not-for-production-use"
    jwt_algorithm: str = "HS256"
    access_token_ttl_s: int = 900          # 15 minutes
    refresh_token_ttl_s: int = 60 * 60 * 24 * 7  # 7 days

    @property
    def jwt_secret_is_dev_default(self) -> bool:
        return self.jwt_secret == "dev-insecure-change-me-not-for-production-use"

    # --- observability + rate limits -----------------------------------
    log_json: bool = False              # emit one JSON object per log line
    log_level: str = "INFO"
    # Fixed-window (per minute) limits. 0 disables. In-process only — a
    # multi-instance deployment needs a shared store (Redis).
    trace_rate_per_min: int = 30
    login_rate_per_min: int = 10


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    settings = Settings()
    if settings.environment == "production" and settings.jwt_secret_is_dev_default:
        raise RuntimeError("AEGIS_JWT_SECRET must be set in production")
    return settings
