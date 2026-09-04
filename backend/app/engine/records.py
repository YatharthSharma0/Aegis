"""Provenance-preserving internal records.

Provider adapters (Phase 1B+) turn raw API responses into these records *before*
anything else touches the data. They deliberately sit between the provider's
wire format and the UI-facing :mod:`app.engine.result` types so that:

* every value movement keeps a link (``snapshot_id``) back to the exact recorded
  :class:`ProviderSnapshot` it came from, and
* chain-specific heuristics have the fields they need (block height/hash, tx
  status, token identity, timestamps) without re-parsing provider JSON.

All records are immutable and reject unknown fields. Decimal amounts are
quantized to the asset's precision on construction so canonical hashing is
stable.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.engine.canonical import SCHEMA_VERSION

Address = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
HexHash = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


class Chain(StrEnum):
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    TRON = "tron"
    BNB = "bnb"
    POLYGON = "polygon"
    SOLANA = "solana"


class AssetKind(StrEnum):
    NATIVE = "native"
    TOKEN = "token"


class TxStatus(StrEnum):
    SUCCESS = "success"
    REVERTED = "reverted"


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Asset(_Record):
    """Identity of the thing being moved (native coin or a specific token)."""

    chain: Chain
    kind: AssetKind
    symbol: str = Field(min_length=1)
    decimals: int = Field(ge=0, le=36)
    # Token contract address; must be absent for native assets, present for tokens.
    contract: Address | None = None

    @model_validator(mode="after")
    def _contract_matches_kind(self) -> Asset:
        if self.kind is AssetKind.NATIVE and self.contract is not None:
            raise ValueError("native asset must not carry a contract address")
        if self.kind is AssetKind.TOKEN and not self.contract:
            raise ValueError("token asset must carry a contract address")
        return self


class BlockRef(_Record):
    """A point on a chain's ledger. Pins the state a snapshot was read at."""

    chain: Chain
    height: int = Field(ge=0)
    block_hash: HexHash
    timestamp: AwareDatetime


class ProviderSnapshot(_Record):
    """Recorded metadata for one provider response. The unit of reproducibility."""

    snapshot_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    chain: Chain
    endpoint: str = Field(min_length=1)
    request_params: dict[str, str] = Field(default_factory=dict)
    captured_at: AwareDatetime
    tip_block: BlockRef
    # sha256 hex of the raw response bytes, as returned by canonical.sha256_hex.
    response_checksum: str = Field(min_length=64, max_length=64)
    record_count: int = Field(ge=0)
    schema_version: str = SCHEMA_VERSION
    notes: str = ""

    def __canonical__(self) -> dict[str, object]:
        # Explicit field list: any volatile field added later (fetch latency,
        # local cache path, ...) is excluded from the hash unless named here.
        return {
            "snapshot_id": self.snapshot_id,
            "provider": self.provider,
            "chain": self.chain,
            "endpoint": self.endpoint,
            "request_params": self.request_params,
            "captured_at": self.captured_at,
            "tip_block": self.tip_block,
            "response_checksum": self.response_checksum,
            "record_count": self.record_count,
            "schema_version": self.schema_version,
            "notes": self.notes,
        }


class Transfer(_Record):
    """One asset movement between two addresses. The atom the walk consumes."""

    asset: Asset
    from_address: Address
    to_address: Address
    value: Decimal = Field(ge=0)
    value_raw: int = Field(ge=0)
    tx_hash: HexHash
    log_index: int | None = Field(default=None, ge=0)
    block_height: int = Field(ge=0)
    block_hash: HexHash
    timestamp: AwareDatetime
    snapshot_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _checks(self) -> Transfer:
        if not self.value.is_finite():
            raise ValueError("transfer value must be finite")
        scale = Decimal(1).scaleb(-self.asset.decimals)
        if self.value != self.value.quantize(scale):
            raise ValueError(
                f"value {self.value} is not quantized to the asset's "
                f"{self.asset.decimals} decimals; quantize before constructing"
            )
        expected_raw = int(self.value.scaleb(self.asset.decimals))
        if expected_raw != self.value_raw:
            raise ValueError(
                f"value {self.value} and value_raw {self.value_raw} disagree "
                f"for {self.asset.decimals}-decimal asset (expected {expected_raw})"
            )
        return self


class NormalizedTransaction(_Record):
    """A whole transaction, with its decoded transfers."""

    chain: Chain
    tx_hash: HexHash
    status: TxStatus
    block: BlockRef
    from_address: Address
    to_address: Address | None = None
    fee: Decimal | None = Field(default=None, ge=0)
    transfers: tuple[Transfer, ...] = ()
    snapshot_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _transfers_belong_to_tx(self) -> NormalizedTransaction:
        for transfer in self.transfers:
            if transfer.tx_hash != self.tx_hash:
                raise ValueError("transfer.tx_hash does not match its transaction")
            if transfer.snapshot_id != self.snapshot_id:
                raise ValueError("transfer.snapshot_id does not match its transaction")
        return self


class AddressActivity(_Record):
    """Summary of an address's on-chain footprint, for entity heuristics."""

    chain: Chain
    address: Address
    is_contract: bool
    first_seen: AwareDatetime | None = None
    last_seen: AwareDatetime | None = None
    transfer_count: int = Field(ge=0)
    snapshot_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _seen_order(self) -> AddressActivity:
        if (
            self.first_seen is not None
            and self.last_seen is not None
            and self.first_seen > self.last_seen
        ):
            raise ValueError("first_seen is after last_seen")
        return self
