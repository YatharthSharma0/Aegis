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
    # Only "fixture" today; "live" (TronGrid) arrives in execution-plan Phase 4.5.
    provider_mode: Literal["fixture"] = "fixture"
    fixture_id: str = "growjoy_tron_trc20"
    # Label packs applied to every trace (attribution). Empty = no attribution.
    label_packs: list[str] = ["aegis_demo_pack"]

    # --- persistence -------------------------------------------------------
    # SQLAlchemy URL. Local dev default is a file SQLite DB; Compose sets
    # postgresql+psycopg://…. Alembic reads this too.
    database_url: str = "sqlite:///./aegis.db"
    # Log SQL. Never true in production.
    db_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
