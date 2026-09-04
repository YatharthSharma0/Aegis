/**
 * Investigation report + SAHYOG notice draft.
 *
 * The backend types these endpoints as open objects, so these interfaces are
 * hand-written to mirror `backend/app/domain/reports.py` (`build_report` /
 * `build_sahyog_notice`). Keep them in sync with that module — they are not
 * covered by `npm run gen:api`.
 */
import { get, post } from "./client";

export interface ReportEvidence {
  provider: string;
  snapshot_id: string;
  tx_hash: string | null;
  block_height: number | null;
  block_hash: string | null;
}

export interface ReportCandidate {
  rank: number;
  tier: string;
  verified: boolean;
  name: string | null;
  label: string | null;
  source: string;
  confidence: string;
  confidence_formula: {
    terms: Record<string, string>;
    weights: Record<string, string>;
    raw_score: string;
    score: string;
  } | null;
  deposit_address: string | null;
  hops_from_seed: number;
  reaching_paths: number;
  signals: string[];
  evidence: ReportEvidence[];
}

export interface FundFlowStep {
  step: number;
  from: string;
  to: string;
  value: string;
  asset: string;
  victim_taint: string;
  tx_hash: string;
  block_height: number;
  timestamp: string;
  provider: string;
  snapshot_id: string;
}

export interface DataSource {
  provider: string;
  endpoint: string;
  captured_at: string;
  response_checksum: string;
  tip_block: { height: number; hash: string };
  record_count: number;
  notes: string | null;
}

export interface InvestigationReport {
  report_type: string;
  header: {
    trace_id: string;
    case_id: string | null;
    reported_address: string;
    chain: string;
    status: string;
    partial_reason: string | null;
    generated_at: string;
    generated_by: string | null;
    block_heights: Record<string, number>;
    result_hash: string;
  };
  officer_summary: string;
  vasp_candidates: ReportCandidate[];
  fund_flow: FundFlowStep[];
  typologies: Array<{
    name: string;
    score: string;
    model: string;
    addresses: string[];
  }>;
  trail_events: Array<{
    reason: string;
    address: string | null;
    asset: string | null;
    amount: string | null;
  }>;
  data_sources: DataSource[];
  certification: {
    statement: string;
    method: string;
    reproducibility_anchor: string;
    generated_at: string;
  };
  caveats: string[];
}

export interface SahyogNoticeParams {
  vasp_rank?: number;
  requesting_officer?: string | null;
  case_ref?: string | null;
  legal_basis?: string | null;
}

export interface SahyogNoticeDraft {
  notice_draft: {
    to: string;
    subject: string;
    body_markdown: string;
    legal_basis: string;
    attachments: string[];
    editable: boolean;
  };
  based_on: {
    trace_id: string;
    vasp_rank: number;
    result_hash: string;
  };
}

export const getReport = (id: string, signal?: AbortSignal) =>
  get<InvestigationReport>(
    `/api/v1/trace/${encodeURIComponent(id)}/report`,
    signal,
  );

export const createSahyogNotice = (id: string, params: SahyogNoticeParams) =>
  post<SahyogNoticeDraft>(
    `/api/v1/trace/${encodeURIComponent(id)}/sahyog-notice`,
    params,
  );
