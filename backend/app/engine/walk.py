"""Value-weighted forward trace with haircut taint propagation.

Two phases:

1. **Discovery** — breadth-first from the seed along *outgoing* transfers, bounded
   by ``max_hops`` (BFS depth), ``max_nodes`` / ``max_edges`` budgets, and a
   wall-clock deadline. Mixer / bridge addresses are marked and not expanded
   past. Every provider response is kept as a :class:`ProviderSnapshot`.

2. **Propagation** — the discovered addresses' transfers are replayed in time
   order, keeping each address's running balance and the victim money held in
   it. A spend carries the *haircut ratio* ``victim_held / balance`` as it stands
   at that moment, so clean money already in the wallet dilutes it, money spent
   before the victim funds arrived carries none, and funds that loop between
   wallets keep their taint. An address never passes on more than it holds.
   Balances come from the provider-reported history; a spend larger than the
   visible balance is treated as drawing the whole of it.

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
from decimal import ROUND_DOWN, Decimal

from app.engine.attribution import EndpointContext, attribute
from app.engine.errors import (
    PartialReason,
    ProviderError,
    ProviderRateLimitedError,
    TrailLostReason,
)
from app.engine.labels import LabelSet, LabelType
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
    VaspCandidate,
)
from app.engine.signals import AddressStats, SignalReport, detect_account_signals

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
    labels: LabelSet | None = None


_Pair = tuple[str, str]


@dataclass(frozen=True)
class _Tainted:
    """A transfer that carried victim funds, and how much."""

    transfer: Transfer
    amount: Decimal


@dataclass
class _Replay:
    carried: list[_Tainted] = field(default_factory=list)
    received: dict[str, Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    spent: set[str] = field(default_factory=set)
    """Addresses that sent victim funds onward."""
    spent_after_receipt: set[str] = field(default_factory=set)
    """Addresses with any outgoing transfer after victim funds first arrived."""
    returned_to_seed: bool = False


@dataclass
class _Propagation:
    carried: list[_Tainted]
    spent: set[str]
    spent_after_receipt: set[str]
    trail: list[TrailEvent]
    mixer_on_path: dict[str, bool]
    bridge_hops: dict[str, int]


@dataclass
class _DiscoveredNode:
    address: str
    depth: int
    order: int
    is_contract: bool
    total_in: Decimal
    out_total: Decimal
    outgoing: list[Transfer]
    incoming: list[Transfer]
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
    labels: LabelSet | None = None,
    clock: Clock = time.monotonic,
) -> Investigation:
    """Trace ``asset`` forward from ``seed`` using ``provider``.

    If ``labels`` is given, its ``mixer`` / ``bridge`` addresses extend the
    explicit sets, and VASP attribution runs over the reached endpoints.
    """
    mixers = mixer_addresses
    bridges = bridge_addresses
    if labels is not None:
        mixers = mixers | labels.addresses_of_type(LabelType.MIXER, chain)
        bridges = bridges | labels.addresses_of_type(LabelType.BRIDGE, chain)
    ctx = _Ctx(
        seed=seed,
        chain=chain,
        asset=asset,
        provider=provider,
        params=params or TraceParams(),
        mixers=mixers,
        bridges=bridges,
        clock=clock,
        labels=labels,
    )
    discovery = _discover(ctx)
    propagation = _propagate(ctx, discovery)
    discovery.trail.extend(propagation.trail)
    return _assemble(ctx, discovery, propagation)


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
        incoming=incoming,
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


def _propagate(ctx: _Ctx, discovery: _Discovery) -> _Propagation:
    """Replay the transfers, pruning flows under the thresholds until stable."""
    nodes = discovery.nodes
    pruned: dict[_Pair, TrailEvent] = {}
    while True:
        replay = _replay(ctx, discovery, frozenset(pruned))
        newly = _under_threshold(ctx, replay.carried)
        if not newly:
            break
        pruned.update(newly)

    for address, amount in replay.received.items():
        nodes[address].taint_in = amount
    if ctx.seed in nodes:
        nodes[ctx.seed].taint_in = nodes[ctx.seed].out_total

    trail = [
        event for (src, _), event in pruned.items() if nodes[src].taint_in > 0
    ]
    if replay.returned_to_seed:
        trail.append(TrailEvent(reason=TrailLostReason.CYCLE, address=ctx.seed))

    quantum = Decimal(1).scaleb(-ctx.asset.decimals)
    for address in sorted(nodes, key=lambda a: nodes[a].order):
        node = nodes[address]
        if node.stopped is None or node.taint_in <= 0:
            continue
        # The hop limit only loses a trail if money actually moved on.
        if (
            node.stopped is TrailLostReason.MAX_HOPS
            and address not in replay.spent_after_receipt
        ):
            continue
        trail.append(
            TrailEvent(
                reason=node.stopped,
                address=address,
                asset_symbol=ctx.asset.symbol,
                amount=node.taint_in.quantize(quantum),
            )
        )

    mixer_on_path, bridge_hops = _path_flags(discovery, replay.carried)
    return _Propagation(
        carried=replay.carried,
        spent=replay.spent,
        spent_after_receipt=replay.spent_after_receipt,
        trail=trail,
        mixer_on_path=mixer_on_path,
        bridge_hops=bridge_hops,
    )


def _timeline(discovery: _Discovery) -> list[Transfer]:
    """Every transfer touching a discovered address, once, oldest first."""
    nodes = discovery.nodes
    transfers = [t for node in nodes.values() for t in node.outgoing]
    transfers += [
        t for node in nodes.values() for t in node.incoming if t.from_address not in nodes
    ]

    def key(t: Transfer) -> tuple[int, datetime, int, str, int]:
        # Within one block: outside money first, then upstream senders first.
        sender = nodes.get(t.from_address)
        order = sender.order if sender else -1
        return (t.block_height, t.timestamp, order, t.tx_hash, t.log_index or 0)

    return sorted(transfers, key=key)


def _replay(ctx: _Ctx, discovery: _Discovery, pruned: frozenset[_Pair]) -> _Replay:
    nodes = discovery.nodes
    quantum = Decimal(1).scaleb(-ctx.asset.decimals)
    balance: dict[str, Decimal] = defaultdict(Decimal)
    held: dict[str, Decimal] = defaultdict(Decimal)
    out = _Replay()

    for transfer in _timeline(discovery):
        src, dst, value = transfer.from_address, transfer.to_address, transfer.value
        sender = nodes.get(src)
        tainted = Decimal(0)
        if sender is not None:
            if src in out.received:
                out.spent_after_receipt.add(src)
            if sender.stopped is None:
                if src == ctx.seed:
                    tainted = value  # everything the reported wallet sends
                elif held[src] > 0 and value > 0:
                    share = value * held[src] / max(balance[src], value)
                    tainted = min(held[src], share.quantize(quantum, rounding=ROUND_DOWN))
                    held[src] -= tainted
            balance[src] = max(Decimal(0), balance[src] - value)
        balance[dst] += value

        if tainted <= 0:
            continue
        out.spent.add(src)
        if dst == ctx.seed:
            out.returned_to_seed = True
        elif dst in nodes and (src, dst) not in pruned:
            held[dst] += tainted
            out.received[dst] += tainted
            out.carried.append(_Tainted(transfer, tainted))
    return out


def _under_threshold(ctx: _Ctx, carried: list[_Tainted]) -> dict[_Pair, TrailEvent]:
    """Sender-recipient flows whose combined taint is too small to follow."""
    totals: dict[_Pair, list[Decimal]] = defaultdict(lambda: [Decimal(0), Decimal(0)])
    for item in carried:
        total = totals[(item.transfer.from_address, item.transfer.to_address)]
        total[0] += item.amount
        total[1] += item.transfer.value

    out: dict[_Pair, TrailEvent] = {}
    for (src, dst), (tainted, value) in totals.items():
        if tainted < ctx.params.min_value:
            out[(src, dst)] = TrailEvent(
                reason=TrailLostReason.MIN_VALUE,
                address=dst,
                asset_symbol=ctx.asset.symbol,
                amount=tainted,
            )
        elif tainted / value < ctx.params.min_taint:
            out[(src, dst)] = TrailEvent(reason=TrailLostReason.MIN_TAINT, address=dst)
    return out


def _path_flags(
    discovery: _Discovery, carried: list[_Tainted]
) -> tuple[dict[str, bool], dict[str, int]]:
    """Which addresses' funds came by way of a wallet that also used a mixer."""
    nodes = discovery.nodes
    fed_mixer = {
        item.transfer.from_address
        for item in carried
        if nodes[item.transfer.to_address].kind is NodeKind.MIXER
    }
    mixer_on_path: dict[str, bool] = defaultdict(bool)
    bridge_hops: dict[str, int] = defaultdict(int)
    for item in carried:
        src, dst = item.transfer.from_address, item.transfer.to_address
        if (mixer_on_path[src] or src in fed_mixer) and nodes[dst].kind is not NodeKind.MIXER:
            mixer_on_path[dst] = True
        inherited = bridge_hops[src] + (1 if nodes[src].kind is NodeKind.BRIDGE else 0)
        bridge_hops[dst] = max(bridge_hops[dst], inherited)
    return dict(mixer_on_path), dict(bridge_hops)


# --------------------------------------------------------------------------
# Phase 3: assemble the Investigation
# --------------------------------------------------------------------------


def _assemble(
    ctx: _Ctx, discovery: _Discovery, propagation: _Propagation
) -> Investigation:
    nodes = discovery.nodes
    for address, node in nodes.items():
        resting = node.stopped is None and address not in propagation.spent
        if resting and node.kind is NodeKind.INTERMEDIARY:
            node.kind = NodeKind.SINK  # the victim funds came to rest here
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
    fraction_quantum = Decimal("1e-12")  # stable taint-fraction precision
    for item in propagation.carried:
        transfer = item.transfer
        snapshot = snap_by_id.get(transfer.snapshot_id)
        graph_edges.append(
            GraphEdge(
                from_address=transfer.from_address,
                to_address=transfer.to_address,
                asset_symbol=transfer.asset.symbol,
                value=transfer.value,
                value_raw=transfer.value_raw,
                taint=min(Decimal(1), item.amount / transfer.value).quantize(
                    fraction_quantum
                ),
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

    vasp_candidates = _attribute(ctx, discovery, propagation, signal_report, graph_edges)

    result = TraceResult(
        vasp_candidates=vasp_candidates,
        graph_nodes=graph_nodes,
        graph_edges=tuple(graph_edges),
        typologies=signal_report.typologies(),
        trail_events=tuple(discovery.trail),
        summary=_summary(ctx.seed, discovery, graph_edges, vasp_candidates),
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


def _attribute(
    ctx: _Ctx,
    discovery: _Discovery,
    propagation: _Propagation,
    signal_report: SignalReport,
    graph_edges: list[GraphEdge],
) -> tuple[VaspCandidate, ...]:
    nodes = discovery.nodes
    seed_out = nodes[ctx.seed].out_total if ctx.seed in nodes else Decimal(0)
    inbound: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in graph_edges:
        inbound[edge.to_address].append(edge)

    endpoints: list[EndpointContext] = []
    for address, node in nodes.items():
        if address == ctx.seed or node.taint_in <= 0:
            continue
        if node.kind in (NodeKind.MIXER, NodeKind.BRIDGE):
            continue
        vasp_sigs = signal_report.vasp_signals_for(address)
        labelled = (
            ctx.labels is not None
            and bool(
                ctx.labels.lookup(
                    address, ctx.chain, types=[LabelType.VASP, LabelType.SERVICE]
                )
            )
        )
        moved_on = address in propagation.spent or (
            node.stopped is TrailLostReason.MAX_HOPS
            and address in propagation.spent_after_receipt
        )
        if not (not moved_on or vasp_sigs or labelled):
            continue
        reaching = inbound.get(address, [])
        endpoints.append(
            EndpointContext(
                address=address,
                chain=ctx.chain,
                hops_from_seed=node.depth,
                taint_retained=(
                    min(Decimal(1), node.taint_in / seed_out) if seed_out > 0 else Decimal(0)
                ),
                reaching_paths=len(reaching) or 1,
                mixer_on_path=propagation.mixer_on_path.get(address, False),
                bridge_hops=propagation.bridge_hops.get(address, 0),
                deposit_address=_deposit_address(ctx, nodes, address, reaching),
                is_sink=not moved_on,
                vasp_signals=vasp_sigs,
                evidence=tuple(e.evidence for e in reaching),
            )
        )
    return attribute(endpoints, ctx.labels)


def _deposit_address(
    ctx: _Ctx,
    nodes: dict[str, _DiscoveredNode],
    endpoint: str,
    reaching: list[GraphEdge],
) -> str:
    """The address to ask the exchange about.

    Normally the matched endpoint itself. When the endpoint is a labelled hot
    wallet, it is the wallet that fed it the most victim funds, provided that
    wallet pays nobody else (the shape of a per-customer deposit address) and is
    not the reported wallet.
    """
    is_hot_wallet = ctx.labels is not None and any(
        "hot_wallet" in label.category
        for label in ctx.labels.lookup(
            endpoint, ctx.chain, types=[LabelType.VASP, LabelType.SERVICE]
        )
    )
    if not is_hot_wallet:
        return endpoint
    fed: dict[str, Decimal] = defaultdict(Decimal)
    for edge in reaching:
        sender = edge.from_address
        if sender != ctx.seed and {t.to_address for t in nodes[sender].outgoing} == {endpoint}:
            fed[sender] += edge.value * edge.taint
    return max(fed, key=lambda a: (fed[a], a)) if fed else endpoint


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


def _summary(
    seed: str,
    discovery: _Discovery,
    edges: list[GraphEdge],
    candidates: tuple[VaspCandidate, ...],
) -> str:
    hops = max((n.depth for n in discovery.nodes.values()), default=0)
    lost = sorted({e.reason.value for e in discovery.trail})
    lost_note = f"; trail-lost: {', '.join(lost)}" if lost else ""
    lead = ""
    if candidates:
        top = candidates[0]
        who = top.name or top.label or "an endpoint"
        lead = f" Nearest off-ramp: {who} ({top.tier.value}, confidence {top.confidence})."
    return (
        f"Traced {len(edges)} tainted transfer(s) over {hops} hop(s) from "
        f"{seed}{lost_note}.{lead}"
    )
