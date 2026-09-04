"""Declarative base.

The schema targets PostgreSQL in production but must also run on SQLite (tests,
local dev without a server), so models avoid PG-only types: JSON via SQLAlchemy's
cross-dialect ``JSON``, timezone-aware ``DateTime(timezone=True)``, string UUIDs.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

_NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_NAMING)
