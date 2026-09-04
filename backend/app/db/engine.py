"""Engine + session factory, built from settings.

One process-wide engine (cached). SQLite gets ``check_same_thread=False`` so
FastAPI's threadpool can share it; a small connection pool otherwise.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.base import Base


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url
    kwargs: dict[str, object] = {"echo": settings.db_echo, "future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True
    return create_engine(url, **kwargs)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """A transactional session. Commits on success, rolls back on error."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all() -> None:
    """Create every table directly (tests / quick local start). Prod uses Alembic."""
    Base.metadata.create_all(get_engine())
