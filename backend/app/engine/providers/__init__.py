"""Chain-data provider adapters + selection.

* :class:`~app.engine.providers.fixture.FixtureProvider` — replays a recorded
  fixture directory; deterministic and offline. The engine's tracing tests and
  the offline demo run against this. Always available, chain-agnostic (the
  fixture's own manifest names its chain).
* :class:`~app.engine.providers.trongrid.TronGridProvider` — live Tron mainnet
  via TronGrid (execution-plan Phase 4.5). Opt-in: selected only via
  :func:`get_provider` with ``mode="live"`` or ``mode="auto"`` plus a key.
"""

from __future__ import annotations

from pathlib import Path

from app.engine.errors import ConfigurationError, UnsupportedChainError
from app.engine.provider import ChainDataProvider
from app.engine.providers.fixture import DEFAULT_FIXTURE_ROOT, FixtureProvider
from app.engine.providers.trongrid import TronGridProvider
from app.engine.records import Chain

__all__ = [
    "DEFAULT_FIXTURE_ROOT",
    "FixtureProvider",
    "TronGridProvider",
    "get_provider",
]


def get_provider(
    chain: Chain,
    mode: str,
    *,
    fixture_id: str = "growjoy_tron_trc20",
    api_key: str | None = None,
    cache_dir: str | Path | None = None,
) -> ChainDataProvider:
    """Select and construct a provider per ``AEGIS_PROVIDER_MODE``.

    ``fixture`` and ``live`` are explicit; ``auto`` picks live only when a
    key is present *and* the chain has a live adapter, so an unconfigured
    deployment silently keeps working in fixture mode rather than failing.
    """
    if mode == "fixture":
        return FixtureProvider(fixture_id)
    if mode == "live":
        return _live_provider(chain, api_key=api_key, cache_dir=cache_dir)
    if mode == "auto":
        if api_key and chain is Chain.TRON:
            return TronGridProvider(api_key=api_key, cache_dir=cache_dir)
        return FixtureProvider(fixture_id)
    raise ConfigurationError(f"unsupported provider mode: {mode!r}")


def _live_provider(
    chain: Chain, *, api_key: str | None, cache_dir: str | Path | None
) -> ChainDataProvider:
    if chain is not Chain.TRON:
        raise UnsupportedChainError(f"no live adapter for chain {chain.value}")
    if not api_key:
        raise ConfigurationError(
            "provider_mode=live requires AEGIS_TRONGRID_API_KEY to be set"
        )
    return TronGridProvider(api_key=api_key, cache_dir=cache_dir)
