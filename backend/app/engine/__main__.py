"""Engine CLI — run one recorded fixture address end to end, offline.

    python -m app.engine trace-fixture --fixture growjoy_tron_trc20
    python -m app.engine trace-fixture --json > investigation.json
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from app.engine.canonical import canonical_json
from app.engine.providers import FixtureProvider
from app.engine.records import Chain
from app.engine.tron import usdt_trc20
from app.engine.walk import forward_trace


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.engine")
    sub = parser.add_subparsers(dest="cmd", required=True)
    trace = sub.add_parser("trace-fixture", help="trace a fixture's seed address")
    trace.add_argument("--fixture", default="growjoy_tron_trc20")
    trace.add_argument("--address", default=None, help="defaults to the fixture seed")
    trace.add_argument("--json", action="store_true", help="print canonical Investigation JSON")
    args = parser.parse_args(argv)

    if args.cmd == "trace-fixture":
        provider = FixtureProvider(args.fixture)
        address = args.address or provider.seed_address
        investigation = forward_trace(
            address, chain=Chain.TRON, asset=usdt_trc20(), provider=provider
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
        for edge in result.graph_edges:
            print(
                f"  {edge.from_address} -> {edge.to_address}  "
                f"{edge.value} {edge.asset_symbol}  taint={edge.taint}"
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
