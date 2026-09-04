import { AlertTriangle, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import type { TraceStatus } from "../api/types";
import { ErrorState } from "../components/ErrorState";
import { GraphCanvas } from "../components/GraphCanvas";
import { HopTimeline } from "../components/HopTimeline";
import { TypologyList } from "../components/TypologyList";
import { VaspMatchCard } from "../components/VaspMatchCard";
import { isTerminal, useTrace, useTraceGraph } from "../features/trace/useTrace";
import { Card } from "../ui/Card";
import { Mono } from "../ui/Mono";
import { Spinner } from "../ui/Spinner";
import { formatDateTime } from "../ui/formatDate";

const RUNNING: TraceStatus[] = ["queued", "running"];

export function TraceResultPage() {
  const { id = "" } = useParams();
  const trace = useTrace(id);
  const status = trace.data?.status;
  const ready = status === "done" || status === "partial";
  const graph = useTraceGraph(id, ready);

  if (trace.isLoading) return <Spinner label="Loading trace" />;
  if (trace.isError || !trace.data) {
    return (
      <div className="mx-auto max-w-3xl space-y-3">
        <ErrorState
          error={trace.error}
          onRetry={() => trace.refetch()}
          context="load the trace"
        />
        <Link to="/cases" className="text-sm text-link hover:underline">
          Back to cases
        </Link>
      </div>
    );
  }

  const t = trace.data;
  const result = t.result;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header>
        <h1 className="text-xl font-bold tracking-tight text-primary">Trace</h1>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
          <Mono value={t.start_address} />
          <span className="uppercase tracking-wide">{t.chain}</span>
          <span>started {formatDateTime(t.created_at)}</span>
          {t.case_id && (
            <Link
              to={`/cases/${t.case_id}`}
              className="text-link hover:underline"
            >
              case {t.case_id}
            </Link>
          )}
          {t.result_hash && (
            <span className="font-mono text-xs" title="Result hash">
              {t.result_hash.slice(0, 12)}…
            </span>
          )}
        </div>
      </header>

      <StatusBanner status={t.status} error={t.error} />

      {RUNNING.includes(t.status) && (
        <Card>
          <Spinner label="Tracing fund flow — this page refreshes automatically" />
        </Card>
      )}

      {isTerminal(t.status) && result && (
        <>
          <Card title="Summary">
            <p className="whitespace-pre-wrap text-sm text-primary">
              {result.summary}
            </p>
          </Card>

          {result.vasp_candidates.length > 0 ? (
            <div className="space-y-4">
              {result.vasp_candidates.map((c, i) => (
                <VaspMatchCard key={c.rank} candidate={c} headline={i === 0} />
              ))}
            </div>
          ) : (
            <Card title="Attributed VASP">
              <p className="text-sm text-muted">
                No exchange or VASP could be attributed for this trace.
              </p>
            </Card>
          )}

          <Card title="Laundering typologies">
            <TypologyList typologies={result.typologies} />
          </Card>

          <Card title="Fund-flow trail">
            <HopTimeline events={result.trail_events} />
          </Card>

          <Card title="Money-flow graph">
            {graph.isLoading && <Spinner label="Loading graph" />}
            {graph.isError && (
              <p className="text-sm text-risk-high" role="alert">
                Could not load the graph.
              </p>
            )}
            {graph.data && (
              <GraphCanvas nodes={graph.data.nodes} edges={graph.data.edges} />
            )}
          </Card>

          <div className="flex gap-2">
            <Link
              to={`/trace/${id}/report`}
              className="rounded-sm bg-brand px-4 py-2 text-sm font-medium text-ink hover:bg-brand-hover"
            >
              Open report
            </Link>
          </div>
        </>
      )}

      {t.status === "failed" && (
        <div className="flex gap-2">
          <Link
            to="/trace/new"
            className="rounded-sm border border-strong px-4 py-2 text-sm font-medium text-secondary hover:bg-hover hover:text-primary"
          >
            Start a new trace
          </Link>
        </div>
      )}
    </div>
  );
}

function StatusBanner({
  status,
  error,
}: {
  status: TraceStatus;
  error: string | null;
}) {
  const map = {
    queued: {
      icon: Loader2,
      className: "border-subtle text-muted",
      text: "Queued — waiting for a worker.",
    },
    running: {
      icon: Loader2,
      className: "border-link/40 text-link",
      text: "Running.",
    },
    done: {
      icon: CheckCircle2,
      className: "border-success/40 text-success",
      text: "Complete.",
    },
    partial: {
      icon: AlertTriangle,
      className: "border-warning/40 text-warning",
      text: "Partial result — the walk hit a limit before finishing.",
    },
    failed: {
      icon: XCircle,
      className: "border-risk-high/40 text-risk-high",
      text: error ?? "The trace failed.",
    },
  }[status];
  const Icon = map.icon;
  return (
    <div
      className={`flex items-center gap-2 rounded-sm border px-3 py-2 text-sm ${map.className}`}
      role="status"
    >
      <Icon size={16} aria-hidden />
      {map.text}
    </div>
  );
}
