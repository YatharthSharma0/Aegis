"""Engine CLI — run one recorded fixture address end to end, offline.

    python -m app.engine trace-fixture --fixture growjoy_tron_trc20
    python -m app.engine trace-fixture --labels aegis_demo_pack
    python -m app.engine trace-fixture --no-labels --json > investigation.json

    # Live (Phase 4.5) — requires AEGIS_TRONGRID_API_KEY:
    python -m app.engine trace-fixture --live --address <real-tron-address>
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from app.engine.canonical import canonical_json
from app.engine.errors import ConfigurationError
from app.engine.labels import LabelSet
from app.engine.providers import FixtureProvider, get_provider
from app.engine.records import Chain
from app.engine.tron import usdt_trc20
from app.engine.walk import forward_trace


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.engine")
    sub = parser.add_subparsers(dest="cmd", required=True)
    trace = sub.add_parser("trace-fixture", help="trace a fixture's seed address")
    trace.add_argument("--fixture", default="growjoy_tron_trc20")
    trace.add_argument("--address", default=None, help="defaults to the fixture seed")
    trace.add_argument("--labels", default="aegis_demo_pack", help="label pack id")
    trace.add_argument("--no-labels", action="store_true", help="run without attribution")
    trace.add_argument("--json", action="store_true", help="print canonical Investigation JSON")
    trace.add_argument(
        "--live", action="store_true",
        help="trace live Tron mainnet via TronGrid instead of the fixture "
             "(requires AEGIS_TRONGRID_API_KEY and --address)",
    )
    args = parser.parse_args(argv)

    if args.cmd == "trace-fixture":
        if args.live:
            if not args.address:
                parser.error("--live requires --address (there is no fixture seed to fall back to)")
            api_key = os.environ.get("AEGIS_TRONGRID_API_KEY")
            if not api_key:
                raise ConfigurationError("AEGIS_TRONGRID_API_KEY is not set")
            cache_dir = os.environ.get("AEGIS_PROVIDER_CACHE_DIR", "./.provider-cache")
            provider = get_provider(
                Chain.TRON, "live", api_key=api_key, cache_dir=cache_dir
            )
            address = args.address
        else:
            provider = FixtureProvider(args.fixture)
            address = args.address or provider.seed_address
        labels = None if args.no_labels else LabelSet.from_pack_ids([args.labels])
        investigation = forward_trace(
            address, chain=Chain.TRON, asset=usdt_trc20(), provider=provider, labels=labels
        )
        if args.json:
            print(canonical_json(investigation).decode())
            return 0
        result = investigation.result
        print(f"status:      {investigation.status.value}")
        print(f"result_hash: {investigation.result_hash()}")
        if result is None:
            return 0
        print(result.summary)
        for candidate in result.vasp_candidates:
            name = candidate.name or candidate.label or "?"
            print(
                f"  #{candidate.rank} {name} [{candidate.tier.value}] "
                f"confidence={candidate.confidence} "
                f"via={candidate.source} hops={candidate.hops_from_seed} "
                f"deposit={candidate.deposit_address}"
            )
        for edge in result.graph_edges:
            print(
                f"  {edge.from_address} -> {edge.to_address}  "
                f"{edge.value} {edge.asset_symbol}  taint={edge.taint}"
            )
        for typ in result.typologies:
            print(
                f"  typology [{typ.name}] score={typ.score} "
                f"at {', '.join(typ.addresses)}"
            )
        for event in result.trail_events:
            print(
                f"  trail-lost [{event.reason.value}] at {event.address} "
                f"amount={event.amount}"
            )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
