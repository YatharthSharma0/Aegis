import type { TrailEventOut } from "../api/types";
import { Mono } from "../ui/Mono";
import { formatDateTime } from "../ui/formatDate";

/** Ordered fund-flow narrative from the engine's trail_events. */
export function HopTimeline({ events }: { events: TrailEventOut[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-muted">No trail events recorded.</p>;
  }
  return (
    <ol className="space-y-3">
      {events.map((e, i) => (
        <li key={i} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span className="mt-1 h-2 w-2 rounded-full bg-brand" aria-hidden />
            {i < events.length - 1 && (
              <span className="w-px flex-1 bg-subtle" aria-hidden />
            )}
          </div>
          <div className="pb-1">
            <div className="text-sm text-primary">{e.reason}</div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted">
              {e.address && <Mono value={e.address} />}
              {e.amount && (
                <span className="font-mono tabular-nums">
                  {e.amount} {e.asset_symbol ?? ""}
                </span>
              )}
              {e.timestamp && <span>{formatDateTime(e.timestamp)}</span>}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
