import { useQuery } from "@tanstack/react-query";

import { getTrace, getTraceGraph } from "../../api/trace";
import type { TraceStatus } from "../../api/types";

export const TERMINAL_STATES: TraceStatus[] = ["done", "partial", "failed"];

export const isTerminal = (s: TraceStatus | undefined) =>
  s !== undefined && TERMINAL_STATES.includes(s);

/** Poll every 2s while the run is queued/running; stop once terminal. */
export function pollInterval(status: TraceStatus | undefined): number | false {
  return isTerminal(status) ? false : 2000;
}

export function useTrace(id: string) {
  return useQuery({
    queryKey: ["trace", id],
    queryFn: ({ signal }) => getTrace(id, signal),
    enabled: id !== "",
    refetchInterval: (query) => pollInterval(query.state.data?.status),
  });
}

/** Graph is only meaningful once the run has produced results. */
export function useTraceGraph(id: string, ready: boolean) {
  return useQuery({
    queryKey: ["trace", id, "graph"],
    queryFn: ({ signal }) => getTraceGraph(id, signal),
    enabled: id !== "" && ready,
  });
}
