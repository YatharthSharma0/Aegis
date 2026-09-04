"""Hash-chain primitive for the audit log.

Each row's ``row_hash`` = sha256 of the canonical JSON of
``{"prev": <previous row_hash>, "fields": <this row's content fields>}``.
``seq`` and ``row_hash`` itself are excluded from ``fields`` — the chain, not the
primary key, is what makes a mutation / deletion / insertion / reorder
detectable.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.engine.canonical import canonical_json, sha256_hex

GENESIS_HASH = "0" * 64

#: Content columns that participate in the hash, in a fixed order.
HASHED_FIELDS = (
    "ts",
    "actor_id",
    "actor_role",
    "action",
    "trace_id",
    "case_id",
    "address",
    "chain",
    "detail",
    "result_hash",
    "request_id",
)


def compute_row_hash(prev_row_hash: str, fields: Mapping[str, object]) -> str:
    ordered = {key: fields.get(key) for key in HASHED_FIELDS}
    return sha256_hex(canonical_json({"prev": prev_row_hash, "fields": ordered}))
