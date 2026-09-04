"""Deterministic serialization and hashing.

Every reproducibility gate in the engine ("the same cached input produces the
same result hash on a clean checkout") is checked against the rules here. They
are intentionally strict — ambiguity is what breaks determinism.

Rules
-----
* **Objects**: keys must be strings; output is sorted lexicographically with no
  insignificant whitespace.
* **Sequences**: order is significant and preserved. ``set`` / ``frozenset`` are
  rejected — sort them into a list first.
* **Decimals**: serialized as fixed-point strings (no exponent). Quantize to the
  asset's precision *before* hashing so ``1.5`` and ``1.50`` don't diverge.
* **Floats**: rejected. Use :class:`~decimal.Decimal`.
* **Datetimes**: must be timezone-aware; converted to UTC and formatted with
  exactly 6 fractional-second digits and a ``Z`` suffix.
* **Dates**: ``YYYY-MM-DD``.
* **Bytes**: lowercase hex, no prefix.
* **Enums**: replaced by their value.
* **Pydantic models / dataclasses**: expanded to their field mapping. A model may
  define ``__canonical__(self) -> object`` to control exactly which fields
  participate (this is how volatile provenance fields are excluded).

The hash is ``"<schema version>:<sha256 hex>"`` so a stored hash announces the
schema it was produced under; bump :data:`SCHEMA_VERSION` on any breaking change
to these rules or to the record shapes.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Protocol, runtime_checkable

SCHEMA_VERSION = "aegis.engine.v1"


@runtime_checkable
class Canonicalizable(Protocol):
    """An object that chooses its own canonical representation."""

    def __canonical__(self) -> object: ...


def _normalize(value: Any) -> Any:  # noqa: PLR0911, PLR0912 — type-dispatch, flat by design
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):  # bool already handled above
        return value
    if isinstance(value, float):
        raise TypeError(
            "float is not allowed in canonical output; use decimal.Decimal"
        )
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"non-finite Decimal is not serializable: {value!r}")
        # Fixed-point, no exponent. ``f"{d:f}"`` keeps the caller's quantization.
        return format(value, "f")
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("naive datetime is not allowed; attach a timezone")
        as_utc = value.astimezone(UTC)
        return as_utc.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Enum):
        return _normalize(value.value)
    if isinstance(value, Canonicalizable):
        return _normalize(value.__canonical__())
    # Pydantic v2 model (avoid importing pydantic here to keep this module leaf).
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump) and hasattr(type(value), "model_fields"):
        return _normalize(model_dump(mode="python"))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _normalize(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"object keys must be strings, got {type(key).__name__}")
            out[key] = _normalize(item)
        return out
    if isinstance(value, (set, frozenset)):
        raise TypeError("set/frozenset is not allowed; sort into a list first")
    if isinstance(value, Sequence):
        return [_normalize(item) for item in value]
    raise TypeError(f"cannot canonicalize value of type {type(value).__name__}")


def canonical_json(value: Any) -> bytes:
    """Return the canonical UTF-8 JSON encoding of ``value``."""
    return json.dumps(
        _normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Lowercase SHA-256 hex digest of raw bytes (used for response checksums)."""
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value: Any, *, schema_version: str = SCHEMA_VERSION) -> str:
    """Return ``"<schema version>:<sha256 hex>"`` for ``value``."""
    return f"{schema_version}:{sha256_hex(canonical_json(value))}"
