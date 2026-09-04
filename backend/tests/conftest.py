"""Test-wide setup: point persistence at a throwaway SQLite database.

The env var is set before anything imports app settings so ``get_settings()``
picks it up; the DB imports come after.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

_TMP_DB = Path(tempfile.gettempdir()) / "aegis-test.db"
os.environ.setdefault("AEGIS_DATABASE_URL", f"sqlite:///{_TMP_DB}")
# Tests drive the worker explicitly; don't let the app lifespan spawn a thread.
os.environ.setdefault("AEGIS_TRACE_WORKER", "external")

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db.engine import create_all, session_scope  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    _TMP_DB.unlink(missing_ok=True)
    create_all()
    yield
    _TMP_DB.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    yield
    with session_scope() as session:
        for table in ("audit_log", "trace_runs", "refresh_tokens", "users"):
            session.execute(text(f"DELETE FROM {table}"))
