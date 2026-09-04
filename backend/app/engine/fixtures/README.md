# Engine fixtures

Recorded provider data the engine's tracing tests and the offline demo run
against, replayed by `app.engine.providers.fixture.FixtureProvider`.

Each fixture is a directory with:

| File | Contents |
|---|---|
| `manifest.json` | id, `synthetic` flag, description, chain, `captured_at`, `tip_block`, and a `files` map of `name → {sha256}` |
| `transfers.json` | TronGrid-shaped TRC-20 transfer records |
| `activity.json` | per-address footprint (`is_contract`, first/last seen, count) |

`FixtureProvider` verifies every file against its manifest checksum on load — a
hand-edit without regenerating fails with `FixtureError`.

## `growjoy_tron_trc20`

**Synthetic — not real chain data.** Hand-built by `growjoy_tron_trc20/_build.py`.
Models a task-scam USDT-on-Tron cash-out:

```
seed ──1499.5──▶ rot1 ──1499.5──▶ rot2 ──1400──▶ cons ──2200──▶ dep ──2200──▶ exch_hot
                                    └────99.5────▶ mixer   (trail lost)
                   rot3 ────────────800──────────▶ cons     (fan-in)
```

Addresses are base58check-valid Tron addresses derived deterministically from
labels; they correspond to no real entity. Regenerate with:

```bash
python -m app.engine.fixtures.growjoy_tron_trc20._build
```

A fixture recorded from live TronGrid (real address, documented provenance) can
be added later without any engine-contract change.
