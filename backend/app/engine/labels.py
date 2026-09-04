"""Versioned attribution label packs.

A label pack is a directory: ``manifest.json`` (id, source, licence,
last-verified date, description, per-file sha256) + ``labels.json`` (the label
records). Packs are loaded and merged into a :class:`LabelSet`, which keeps each
label's originating pack so a report can cite *which* source said what and how
old it is.

**VASP labels and sanctions evidence are different things.** ``LabelType.VASP`` /
``SERVICE`` answer "which exchange is this"; ``LabelType.SANCTIONS`` is a
watchlist flag, not a VASP directory. The two never merge — attribution reads
them via separate queries.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.engine.canonical import sha256_hex
from app.engine.errors import FixtureError
from app.engine.records import Chain

DEFAULT_LABEL_ROOT = Path(__file__).resolve().parent / "fixtures" / "labels"

Address = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


class LabelType(StrEnum):
    VASP = "vasp"           # a centralised exchange / custodial service
    SERVICE = "service"     # other identified on-chain service (non-custodial)
    SANCTIONS = "sanctions" # OFAC / watchlist flag — NOT a VASP directory
    MIXER = "mixer"
    BRIDGE = "bridge"


class Label(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    address: Address
    chain: Chain
    label_type: LabelType
    entity_name: str | None = None
    category: str = ""
    confidence: Decimal = Field(default=Decimal("0.9"), ge=0, le=1)
    pack_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    last_verified: date

    def __canonical__(self) -> dict[str, object]:
        return {
            "address": self.address,
            "chain": self.chain,
            "label_type": self.label_type,
            "entity_name": self.entity_name,
            "category": self.category,
            "confidence": self.confidence,
            "pack_id": self.pack_id,
            "source": self.source,
            "last_verified": self.last_verified,
        }


class LabelPackMeta(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pack_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    licence: str = Field(min_length=1)
    last_verified: date
    description: str = ""
    synthetic: bool = False


class LabelPack:
    """One loaded label pack, checksum-verified against its manifest."""

    def __init__(self, pack_id: str, *, root: Path = DEFAULT_LABEL_ROOT) -> None:
        self.pack_id = pack_id
        directory = root / pack_id
        if not directory.is_dir():
            raise FixtureError(f"label pack not found: {directory}")

        raw_manifest: dict[str, Any] = _load_json(directory, "manifest.json", pack_id)
        for name, meta in raw_manifest.get("files", {}).items():
            actual = sha256_hex((directory / name).read_bytes())
            if actual != meta["sha256"]:
                raise FixtureError(
                    f"label pack {pack_id}: {name} checksum mismatch"
                )
        self.meta = LabelPackMeta(
            pack_id=raw_manifest["pack_id"],
            source=raw_manifest["source"],
            licence=raw_manifest["licence"],
            last_verified=date.fromisoformat(raw_manifest["last_verified"]),
            description=raw_manifest.get("description", ""),
            synthetic=bool(raw_manifest.get("synthetic", False)),
        )

        rows: list[dict[str, Any]] = _load_json(directory, "labels.json", pack_id)
        self.labels: tuple[Label, ...] = tuple(
            Label(
                address=row["address"],
                chain=Chain(row["chain"]),
                label_type=LabelType(row["label_type"]),
                entity_name=row.get("entity_name"),
                category=row.get("category", ""),
                confidence=Decimal(str(row.get("confidence", "0.9"))),
                pack_id=self.pack_id,
                source=raw_manifest["source"],
                last_verified=date.fromisoformat(
                    row.get("last_verified", raw_manifest["last_verified"])
                ),
            )
            for row in rows
        )


class LabelSet:
    """A merge of one or more label packs, retaining per-label provenance."""

    def __init__(self, packs: Iterable[LabelPack]) -> None:
        self.packs = tuple(packs)
        self._by_key: dict[tuple[str, str], list[Label]] = {}
        for pack in self.packs:
            for label in pack.labels:
                self._by_key.setdefault((label.address, label.chain.value), []).append(label)

    @classmethod
    def from_pack_ids(
        cls, pack_ids: Iterable[str], *, root: Path = DEFAULT_LABEL_ROOT
    ) -> LabelSet:
        return cls(LabelPack(pid, root=root) for pid in pack_ids)

    def lookup(
        self, address: str, chain: Chain, *, types: Iterable[LabelType] | None = None
    ) -> tuple[Label, ...]:
        found = self._by_key.get((address, chain.value), [])
        if types is not None:
            allowed = set(types)
            found = [label for label in found if label.label_type in allowed]
        return tuple(found)

    def addresses_of_type(self, label_type: LabelType, chain: Chain) -> frozenset[str]:
        return frozenset(
            label.address
            for labels in self._by_key.values()
            for label in labels
            if label.label_type is label_type and label.chain is chain
        )

    def provenance(self) -> tuple[LabelPackMeta, ...]:
        return tuple(pack.meta for pack in self.packs)


def _load_json(directory: Path, name: str, pack_id: str) -> Any:
    try:
        return json.loads((directory / name).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FixtureError(f"label pack {pack_id}: missing {name}") from exc
    except json.JSONDecodeError as exc:
        raise FixtureError(f"label pack {pack_id}: {name} is not valid JSON") from exc
