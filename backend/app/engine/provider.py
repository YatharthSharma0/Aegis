"""The read-only chain-data provider interface.

An adapter (Phase 1B: TronGrid; Phase 1D: an Ethereum provider) implements
:class:`ChainDataProvider`. The engine only ever reads — no adapter signs,
broadcasts, or writes anything on-chain.

Every method returns its data *together with* the :class:`ProviderSnapshot` it
came from, so the caller can attach provenance without trusting the adapter to
have done it. Pagination is cursor-based and opaque: the caller passes back
whatever ``next_cursor`` it received.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from app.engine.records import (
    Address,
    AddressActivity,
    Asset,
    BlockRef,
    Chain,
    NormalizedTransaction,
    ProviderSnapshot,
)

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 200


class TransferPage(BaseModel):
    """One page of normalized transactions plus its provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    transactions: tuple[NormalizedTransaction, ...]
    snapshot: ProviderSnapshot
    # Opaque; ``None`` means no more pages.
    next_cursor: str | None = None

    @property
    def has_more(self) -> bool:
        return self.next_cursor is not None


class ActivityResult(BaseModel):
    """An address-activity summary plus its provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    activity: AddressActivity
    snapshot: ProviderSnapshot


class BlockResult(BaseModel):
    """A block reference plus its provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    block: BlockRef
    snapshot: ProviderSnapshot


@runtime_checkable
class ChainDataProvider(Protocol):
    """Read-only access to one chain's transfer history and block state."""

    #: Stable identifier recorded in every snapshot (e.g. ``"trongrid"``).
    name: str
    #: The single chain this adapter serves.
    chain: Chain

    def latest_block(self) -> BlockResult:
        """Return the current chain tip. Pins the ledger state for a trace run."""
        ...

    def token_transfers(  # noqa: PLR0913 — an explicit provider query surface
        self,
        address: Address,
        *,
        asset: Asset,
        cursor: str | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        start_block: int | None = None,
        end_block: int | None = None,
    ) -> TransferPage:
        """Return one page of ``asset`` transfers touching ``address``.

        Implementations must apply timeout, retry-with-backoff, and rate-limit
        handling, and must raise the appropriate
        :class:`~app.engine.errors.ProviderError` subclass on failure rather
        than returning a partial page silently.
        """
        ...

    def address_activity(self, address: Address) -> ActivityResult:
        """Return a footprint summary for ``address`` (contract flag, seen range)."""
        ...


class ProviderCapabilities(BaseModel):
    """What a provider can and cannot do — surfaced in reports for honesty."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field(min_length=1)
    chain: Chain
    supports_token_transfers: bool = True
    supports_internal_transfers: bool = False
    supports_event_logs: bool = False
    max_page_size: int = MAX_PAGE_SIZE
    notes: str = ""
