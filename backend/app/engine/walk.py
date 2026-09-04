"""Value-weighted forward trace with haircut taint propagation.

Two phases:

1. **Discovery** — breadth-first from the seed along *outgoing* transfers, bounded
   by ``max_hops`` (BFS depth), ``max_nodes`` / ``max_edges`` budgets, and a
   wall-clock deadline. Mixer / bridge addresses are marked and not expanded
   past. Every provider response is kept as a :class:`ProviderSnapshot`.

2. **Propagation** — the discovered graph, restricted to discovery-order-forward
   edges (which makes it a DAG), is walked in topological order. Each address's
   *haircut ratio* is ``victim_taint_in / total_in`` using the provider-reported
   total inflow, so clean money flowing into a mixing point dilutes the victim
   fraction correctly. Taint handed to each outgoing edge is proportional to its
   value; the sum handed out never exceeds what came in.

The result is an :class:`Investigation` whose ``result_hash()`` is stable across
runs on the same cached input. This phase fills ``graph_nodes`` (with structural
``typologies`` from :mod:`app.engine.signals`), ``graph_edges``, ``typologies``
and ``trail_events``. VASP attribution and clustering are added in Phase 1C.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from app.engine.errors import (
    PartialReason,
    ProviderError,
    ProviderRateLimitedError,
    TrailLostReason,
)
from app.engine.provider import ChainDataProvider
from app.engine.records import Asset, Chain, ProviderSnapshot, Transfer
from app.engine.result import (
    EvidenceRef,
    GraphEdge,
    GraphNode,
    Investigation,
    NodeKind,
    TraceParams,
    TraceResult,
    TraceStatus,
    TrailEvent,
)
from app.engine.signals import AddressStats, detect_account_signals

Clock = Callable[[], float]


@dataclass(frozen=True)
class _Ctx:
    """Everything one trace run needs, passed as a single object."""

    seed: str
    chain: Chain
    asset: Asset
    provider: ChainDataProvider
    params: TraceParams
    mixers: frozenset[str]
    bridges: frozenset[str]
    clock: Clock


@dataclass
class _DiscoveredNode:
    address: str
    depth: int
    order: int
    is_contract: bool
    total_in: Decimal
    out_total: Decimal
    outgoing: list[Transfer]
    kind: NodeKind
    distinct_senders: int = 0
    distinct_recipients: int = 0
    incoming_count: int = 0
    outgoing_count: int = 0
    largest_out_fraction: Decimal = Decimal(0)
    first_activity: datetime | None = None
    last_activity: datetime | None = None
    forward_latency_s: Decimal | None = None
    stopped: TrailLostReason | None = None
    taint_in: Decimal = Decimal(0)


@dataclass
class _Discovery:
    nodes: dict[str, _DiscoveredNode] = field(default_factory=dict)
    edges: list[Transfer] = field(default_factory=list)
    trail: list[TrailEvent] = field(default_factory=list)
    snapshots: list[ProviderSnapshot] = field(default_factory=list)
    block_heights: dict[Chain, int] = field(default_factory=dict)
    partial_reason: PartialReason | None = None


def forward_trace(  # noqa: PLR0913 — the public trace input surface
    seed: str,
    *,
    chain: Chain,
    asset: Asset,
    provider: ChainDataProvider,
    params: TraceParams | None = None,
    mixer_addresses: frozenset[str] = frozenset(),
    bridge_addresses: frozenset[str] = frozenset(),
    clock: Clock = time.monotonic,
) -> Investigation:
    """Trace ``asset`` forward from ``seed`` using ``provider``."""
    ctx = _Ctx(
        seed=seed,
        chain=chain,
        asset=asset,
        provider=provider,
        params=params or TraceParams(),
        mixers=mixer_addresses,
        bridges=bridge_addresses,
        clock=clock,
    )
    discovery = _discover(ctx)
    edge_taint, prune_trail = _propagate(ctx, discovery)
    discovery.trail.extend(prune_trail)
    return _assemble(ctx, discovery, edge_taint)


# --------------------------------------------------------------------------
# Phase 1: discovery
# --------------------------------------------------------------------------


def _discover(ctx: _Ctx) -> _Discovery:
    out = _Discovery()
    started = ctx.clock()

    tip = ctx.provider.latest_block()
    out.block_heights[ctx.chain] = tip.block.height
    _add_snapshot(out, tip.snapshot)

    queue: deque[tuple[str, int]] = deque([(ctx.seed, 0)])
    order = 0
    deadline = float(ctx.params.total_deadline_s)

    while queue:
        if ctx.clock() - started > deadline:
            out.partial_reason = PartialReason.DEADLINE
            break

        address, depth = queue.popleft()
        if address in out.nodes:
            continue

        try:
            activity = ctx.provider.address_activity(address)
            _add_snapshot(out, activity.snapshot)
            transfers = _fetch_all_transfers(out, ctx, address)
        except ProviderRateLimitedError:
            out.partial_reason = PartialReason.PROVIDER_RATE_LIMITED
            break
        except ProviderError:
            out.partial_reason = PartialReason.PROVIDER_UNAVAILABLE
            break

        node = _make_node(ctx, address, depth, order, transfers, activity.activity.is_contract)
        order += 1
        out.nodes[address] = node
        _expand(ctx, out, node, queue)

        if len(out.nodes) >= ctx.params.max_nodes:
            out.partial_reason = PartialReason.NODE_BUDGET
            break
        if len(out.edges) >= ctx.params.max_edges:
            out.partial_reason = PartialReason.EDGE_BUDGET
            break

    return out


def _make_node(  # noqa: PLR0913, PLR0917 — internal node constructor
    ctx: _Ctx,
    address: str,
    depth: int,
    order: int,
    transfers: list[Transfer],
    is_contract: bool,
) -> _DiscoveredNode:
    incoming = [t for t in transfers if t.to_address == address]
    outgoing = sorted(
        (t for t in transfers if t.from_address == address),
        key=lambda t: (t.block_height, t.timestamp, t.tx_hash, t.log_index or 0),
    )
    out_total = sum((t.value for t in outgoing), Decimal(0))
    per_recipient: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for transfer in outgoing:
        per_recipient[transfer.to_address] += transfer.value
    largest_out = max(per_recipient.values(), default=Decimal(0))
    all_ts = [t.timestamp for t in transfers]
    latency = None
    if incoming and outgoing:
        gap = min(t.timestamp for t in outgoing) - max(t.timestamp for t in incoming)
        if gap.total_seconds() > 0:
            latency = Decimal(str(gap.total_seconds()))

    return _DiscoveredNode(
        address=address,
        depth=depth,
        order=order,
        is_contract=is_contract,
        total_in=sum((t.value for t in incoming), Decimal(0)),
        out_total=out_total,
        outgoing=outgoing,
        kind=_classify(ctx, address, outgoing),
        distinct_senders=len({t.from_address for t in incoming}),
        distinct_recipients=len(per_recipient),
        incoming_count=len(incoming),
        outgoing_count=len(outgoing),
        largest_out_fraction=(largest_out / out_total) if out_total > 0 else Decimal(0),
        first_activity=min(all_ts, default=None),
        last_activity=max(all_ts, default=None),
        forward_latency_s=latency,
    )


def _expand(
    ctx: _Ctx, out: _Discovery, node: _DiscoveredNode, queue: deque[tuple[str, int]]
) -> None:
    """Record a stop reason, or enqueue the node's children."""
    if node.kind is NodeKind.MIXER:
        node.stopped = TrailLostReason.MIXER_LIKE
    elif node.kind is NodeKind.BRIDGE:
        node.stopped = TrailLostReason.BRIDGE
    elif not node.outgoing:
        return  # a natural sink
    elif node.depth + 1 > ctx.params.max_hops:
        node.stopped = TrailLostReason.MAX_HOPS
    else:
        for transfer in node.outgoing:
            out.edges.append(transfer)
            if transfer.to_address not in out.nodes:
                queue.append((transfer.to_address, node.depth + 1))


def _fetch_all_transfers(out: _Discovery, ctx: _Ctx, address: str) -> list[Transfer]:
    transfers: list[Transfer] = []
    cursor: str | None = None
    while True:
        page = ctx.provider.token_transfers(address, asset=ctx.asset, cursor=cursor)
        _add_snapshot(out, page.snapshot)
        for tx in page.transactions:
            transfers.extend(tx.transfers)
        if page.next_cursor is None:
            break
        cursor = page.next_cursor
    return transfers


def _classify(ctx: _Ctx, address: str, outgoing: list[Transfer]) -> NodeKind:
    if address == ctx.seed:
        return NodeKind.SEED
    if address in ctx.mixers:
        return NodeKind.MIXER
    if address in ctx.bridges:
        return NodeKind.BRIDGE
    if not outgoing:
        return NodeKind.SINK
    return NodeKind.INTERMEDIARY


def _add_snapshot(out: _Discovery, snapshot: ProviderSnapshot) -> None:
    if all(s.snapshot_id != snapshot.snapshot_id for s in out.snapshots):
        out.snapshots.append(snapshot)


# --------------------------------------------------------------------------
# Phase 2: haircut taint propagation
# --------------------------------------------------------------------------


def _propagate(
    ctx: _Ctx, discovery: _Discovery
) -> tuple[dict[tuple[str, str], Decimal], list[TrailEvent]]:
    """Return per-(from,to) taint fraction and trail events from pruning."""
    nodes = discovery.nodes
    trail: list[TrailEvent] = []

    forward_flow: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal(0))
    for transfer in discovery.edges:
        src, dst = transfer.from_address, transfer.to_address
        if src not in nodes or dst not in nodes:
            continue
        if nodes[dst].order > nodes[src].order:
            forward_flow[(src, dst)] += transfer.value
        else:
            trail.append(TrailEvent(reason=TrailLostReason.CYCLE, address=dst))

    successors: dict[str, list[str]] = defaultdict(list)
    for src, dst in forward_flow:
        successors[src].append(dst)

    quantum = Decimal(1).scaleb(-ctx.asset.decimals)
    fraction_quantum = Decimal("1e-12")  # stable taint-fraction precision
    taint_in: dict[str, Decimal] = (
        {ctx.seed: nodes[ctx.seed].out_total} if ctx.seed in nodes else {}
    )
    edge_taint: dict[tuple[str, str], Decimal] = {}

    for address in sorted(nodes, key=lambda a: nodes[a].order):
        node = nodes[address]
        received = taint_in.get(address, Decimal(0))
        node.taint_in = received
        if received <= 0:
            continue
        if node.stopped is not None:
            trail.append(
                TrailEvent(
                    reason=node.stopped,
                    address=address,
                    asset_symbol=ctx.asset.symbol,
                    amount=received.quantize(quantum),
                )
            )
            continue
        if not node.outgoing:
            continue  # taint rests at a sink

        distributable = min(received, node.out_total)
        for dst in sorted(successors.get(address, []), key=lambda a: nodes[a].order):
            value = forward_flow[(address, dst)]
            tainted = (value / node.out_total * distributable).quantize(quantum)
            fraction = (
                min(Decimal(1), tainted / value).quantize(fraction_quantum)
                if value > 0
                else Decimal(0)
            )
            if tainted < ctx.params.min_value:
                trail.append(
                    TrailEvent(
                        reason=TrailLostReason.MIN_VALUE,
                        address=dst,
                        asset_symbol=ctx.asset.symbol,
                        amount=tainted,
                    )
                )
                continue
            if fraction < ctx.params.min_taint:
                trail.append(TrailEvent(reason=TrailLostReason.MIN_TAINT, address=dst))
                continue
            edge_taint[(address, dst)] = fraction
            taint_in[dst] = taint_in.get(dst, Decimal(0)) + tainted

    return edge_taint, trail


# --------------------------------------------------------------------------
# Phase 3: assemble the Investigation
# --------------------------------------------------------------------------


def _assemble(
    ctx: _Ctx, discovery: _Discovery, edge_taint: dict[tuple[str, str], Decimal]
) -> Investigation:
    nodes = discovery.nodes
    snap_by_id = {s.snapshot_id: s for s in discovery.snapshots}

    kept = {ctx.seed} | {a for a, n in nodes.items() if n.taint_in > 0}
    signal_report = detect_account_signals(
        [_stats_for(nodes[a], ctx.seed) for a in kept if a in nodes]
    )
    graph_nodes = tuple(
        GraphNode(
            address=nodes[a].address,
            chain=ctx.chain,
            kind=nodes[a].kind,
            typologies=signal_report.labels_for(a),
        )
        for a in sorted(kept, key=lambda a: nodes[a].order)
        if a in nodes
    )

    graph_edges: list[GraphEdge] = []
    for transfer in discovery.edges:
        key = (transfer.from_address, transfer.to_address)
        if key not in edge_taint:
            continue
        snapshot = snap_by_id.get(transfer.snapshot_id)
        graph_edges.append(
            GraphEdge(
                from_address=transfer.from_address,
                to_address=transfer.to_address,
                asset_symbol=transfer.asset.symbol,
                value=transfer.value,
                value_raw=transfer.value_raw,
                taint=edge_taint[key],
                tx_hash=transfer.tx_hash,
                log_index=transfer.log_index,
                block_height=transfer.block_height,
                timestamp=transfer.timestamp,
                evidence=EvidenceRef(
                    provider=snapshot.provider if snapshot else "unknown",
                    snapshot_id=transfer.snapshot_id,
                    tx_hash=transfer.tx_hash,
                    block_height=transfer.block_height,
                    block_hash=transfer.block_hash,
                    captured_at=snapshot.captured_at if snapshot else None,
                ),
            )
        )

    result = TraceResult(
        graph_nodes=graph_nodes,
        graph_edges=tuple(graph_edges),
        typologies=signal_report.typologies(),
        trail_events=tuple(discovery.trail),
        summary=_summary(ctx.seed, discovery, graph_edges),
    )
    status = TraceStatus.PARTIAL if discovery.partial_reason else TraceStatus.DONE
    now = datetime.now(UTC)
    return Investigation(
        start_address=ctx.seed,
        chain=ctx.chain,
        params=ctx.params,
        status=status,
        partial_reason=discovery.partial_reason,
        block_heights=dict(discovery.block_heights),
        snapshots=tuple(discovery.snapshots),
        result=result,
        started_at=now,
        finished_at=now,
    )


def _stats_for(node: _DiscoveredNode, seed: str) -> AddressStats:
    return AddressStats(
        address=node.address,
        is_seed=node.address == seed,
        is_contract=node.is_contract,
        total_in=node.total_in,
        total_out=node.out_total,
        distinct_senders=node.distinct_senders,
        distinct_recipients=node.distinct_recipients,
        incoming_count=node.incoming_count,
        outgoing_count=node.outgoing_count,
        largest_out_fraction=node.largest_out_fraction,
        first_activity=node.first_activity,
        last_activity=node.last_activity,
        forward_latency_s=node.forward_latency_s,
    )


def _summary(seed: str, discovery: _Discovery, edges: list[GraphEdge]) -> str:
    hops = max((n.depth for n in discovery.nodes.values()), default=0)
    lost = sorted({e.reason.value for e in discovery.trail})
    lost_note = f"; trail-lost: {', '.join(lost)}" if lost else ""
    return f"Traced {len(edges)} tainted transfer(s) over {hops} hop(s) from {seed}{lost_note}."
