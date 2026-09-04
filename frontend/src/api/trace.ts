/** Trace endpoints (`/api/v1/trace`). */
import { get, post } from "./client";
import type {
  TraceAccepted,
  TraceGraphResponse,
  TraceRequest,
  TraceStatusResponse,
} from "./types";

export const startTrace = (body: TraceRequest) =>
  post<TraceAccepted>("/api/v1/trace", body);

export const getTrace = (id: string, signal?: AbortSignal) =>
  get<TraceStatusResponse>(`/api/v1/trace/${encodeURIComponent(id)}`, signal);

export const getTraceGraph = (id: string, signal?: AbortSignal) =>
  get<TraceGraphResponse>(
    `/api/v1/trace/${encodeURIComponent(id)}/graph`,
    signal,
  );
