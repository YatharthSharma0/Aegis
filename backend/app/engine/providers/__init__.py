"""Chain-data provider adapters.

* :class:`~app.engine.providers.fixture.FixtureProvider` — replays a recorded
  fixture directory; deterministic and offline. The engine's tracing tests and
  the offline demo run against this.

A live TronGrid HTTP adapter is a separate follow-up: the real TRC-20 transfer
endpoint returns no block height/hash per record, so wiring it in involves a
deliberate call about per-transfer provenance (relax the records vs. enrich each
tx) that shouldn't ride along here.
"""

from app.engine.providers.fixture import DEFAULT_FIXTURE_ROOT, FixtureProvider

__all__ = ["DEFAULT_FIXTURE_ROOT", "FixtureProvider"]
