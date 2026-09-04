/** Health check + admin audit log. */
import { get } from "./client";
import type { AuditResponse, HealthResponse } from "./types";

export const getHealth = (signal?: AbortSignal) =>
  get<HealthResponse>("/api/v1/health", signal);

export interface AuditParams {
  limit?: number;
  action?: string;
  actor_id?: string;
}

export function getAudit(params: AuditParams = {}, signal?: AbortSignal) {
  const q = new URLSearchParams();
  if (params.limit) q.set("limit", String(params.limit));
  if (params.action) q.set("action", params.action);
  if (params.actor_id) q.set("actor_id", params.actor_id);
  const qs = q.toString();
  return get<AuditResponse>(
    `/api/v1/admin/audit${qs ? `?${qs}` : ""}`,
    signal,
  );
}
