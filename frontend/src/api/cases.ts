/** Case-management endpoints (`/api/v1/cases`). */
import type {
  AddComplaintRequest,
  CaseDetailOut,
  CaseOut,
  CaseStatus,
  ComplaintOut,
  CreateCaseRequest,
  UpdateCaseRequest,
} from "./types";
import { get, patch, post } from "./client";

export interface ListCasesParams {
  status?: CaseStatus;
  mine?: boolean;
  limit?: number;
}

export function listCases(params: ListCasesParams = {}, signal?: AbortSignal) {
  const q = new URLSearchParams();
  if (params.status) q.set("status", params.status);
  if (params.mine) q.set("mine", "true");
  if (params.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return get<CaseOut[]>(`/api/v1/cases${qs ? `?${qs}` : ""}`, signal);
}

export const getCase = (id: string, signal?: AbortSignal) =>
  get<CaseDetailOut>(`/api/v1/cases/${encodeURIComponent(id)}`, signal);

export const createCase = (body: CreateCaseRequest) =>
  post<CaseOut>("/api/v1/cases", body);

export const updateCase = (id: string, body: UpdateCaseRequest) =>
  patch<CaseOut>(`/api/v1/cases/${encodeURIComponent(id)}`, body);

export const addComplaint = (id: string, body: AddComplaintRequest) =>
  post<ComplaintOut>(
    `/api/v1/cases/${encodeURIComponent(id)}/complaints`,
    body,
  );
