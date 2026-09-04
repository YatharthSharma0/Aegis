"""The one place the backend talks to :mod:`app.engine`.

Builds the provider and label set from settings and calls ``forward_trace``.
Keeping this isolated means the switch to a live TronGrid provider
(execution-plan Phase 4.5) is a change here and nowhere else.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from app.engine.labels import LabelSet
from app.engine.provider import ChainDataProvider
from app.engine.providers import get_provider
from app.engine.records import Chain
from app.engine.result import Investigation, TraceParams
from app.engine.tron import usdt_trc20
from app.engine.walk import forward_trace


@lru_cache
def _provider(
    mode: str, fixture_id: str, api_key: str | None, cache_dir: str | None
) -> ChainDataProvider:
    # Cached (not just constructed once): a live provider owns an httpx
    # client and in-memory tx/block caches worth reusing across traces in
    # the same process; a fixture provider is cheap to reuse too.
    return get_provider(
        Chain.TRON, mode, fixture_id=fixture_id, api_key=api_key, cache_dir=cache_dir
    )


@lru_cache
def _labels(pack_ids: tuple[str, ...]) -> LabelSet | None:
    if not pack_ids:
        return None
    return LabelSet.from_pack_ids(pack_ids)


def run_engine(
    start_address: str, chain: Chain, params: TraceParams, *, settings: Settings | None = None
) -> Investigation:
    """Run one forward trace with the configured provider and label packs."""
    cfg = settings or get_settings()
    if chain is not Chain.TRON:
        raise ValueError(f"only Tron is wired up so far, got {chain}")
    provider = _provider(
        cfg.provider_mode, cfg.fixture_id, cfg.trongrid_api_key, cfg.provider_cache_dir
    )
    labels = _labels(tuple(cfg.label_packs))
    return forward_trace(
        start_address,
        chain=chain,
        asset=usdt_trc20(),
        provider=provider,
        params=params,
        labels=labels,
    )
