/**
 * Friendly aliases over the generated OpenAPI schema (src/api/schema.d.ts).
 * Regenerate the schema with `npm run gen:api` after a backend contract change.
 */
import type { components } from "./schema";

type S = components["schemas"];

export type LoginRequest = S["LoginRequest"];
export type RefreshRequest = S["RefreshRequest"];
export type TokenResponse = S["TokenResponse"];
export type MeResponse = S["MeResponse"];

export type TraceRequest = S["TraceRequest"];
export type TraceParamsIn = S["TraceParamsIn"];
export type TraceAccepted = S["TraceAccepted"];
export type TraceStatusResponse = S["TraceStatusResponse"];
export type TraceGraphResponse = S["TraceGraphResponse"];
export type TraceResultOut = S["TraceResultOut"];
export type VaspCandidateOut = S["VaspCandidateOut"];
export type TypologyOut = S["TypologyOut"];
export type TrailEventOut = S["TrailEventOut"];
export type GraphNodeOut = S["GraphNodeOut"];
export type GraphEdgeOut = S["GraphEdgeOut"];

export type CaseOut = S["CaseOut"];
export type CaseDetailOut = S["CaseDetailOut"];
export type CreateCaseRequest = S["CreateCaseRequest"];
export type UpdateCaseRequest = S["UpdateCaseRequest"];
export type AddComplaintRequest = S["AddComplaintRequest"];
export type ComplaintOut = S["ComplaintOut"];
export type TraceRunSummary = S["TraceRunSummary"];
export type CaseStatus = S["CaseStatus"];
export type ComplaintSource = S["ComplaintSource"];

export type AuditResponse = S["AuditResponse"];
export type SahyogNoticeRequest = S["SahyogNoticeRequest"];

export type EvidenceOut = S["EvidenceOut"];

export type TraceStatus = TraceStatusResponse["status"];
export type Chain = S["Chain"];
export type TaintModel = S["TaintModel"];
export type Role = MeResponse["role"];
