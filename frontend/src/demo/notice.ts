/** Port of `build_sahyog_notice` in `backend/app/domain/reports.py`, marked as sample. */
import type { SahyogNoticeDraft, SahyogNoticeParams } from "../api/report";
import type { ReportCandidate, InvestigationReport } from "../api/report";

export const SAMPLE_MARK = "SAMPLE — SYNTHETIC DEMO DATA. NOT FOR ISSUE.";

export function buildNotice(
  report: InvestigationReport,
  candidate: ReportCandidate,
  params: SahyogNoticeParams,
): SahyogNoticeDraft {
  const { header } = report;
  const vasp = candidate.name ?? candidate.label ?? "the receiving VASP";
  const ref = params.case_ref || header.case_id || header.trace_id;
  const basis =
    params.legal_basis || "IT Act s.79(3)(b) read with BNSS provisions on preservation";
  const asset = report.fund_flow[0]?.asset ?? "";
  const traced = report.fund_flow
    .filter((s) => s.to === candidate.deposit_address)
    .reduce((sum, s) => sum + Number(s.value), 0)
    .toFixed(6);

  const body = `${SAMPLE_MARK}

To: ${vasp} — Nodal / Compliance Officer

Subject: Request for preservation of records and account information — ${ref}

1. This office is investigating cyber-financial fraud under reference ${ref}.
   Funds reported by the victim from address ${header.reported_address} on the
   ${header.chain} network have been traced on the public blockchain to a
   deposit address associated with your platform.

2. Deposit address: ${candidate.deposit_address ?? "see technical annex"}
   Traced value reaching this address: ${traced} ${asset}
   Attribution: ${candidate.tier} (confidence ${candidate.confidence}); method and
   full arithmetic are in the attached investigation report (result hash
   ${header.result_hash}).

3. You are requested, under ${basis}, to:
   a. preserve all records, logs and KYC information relating to the account(s)
      linked to the above deposit address, and
   b. provide the account holder's identity and transaction history for the
      relevant period to the undersigned.

4. This is an assistive investigative lead; nothing herein directs a freeze.
   A formal order will follow as warranted.

Requesting officer: ${params.requesting_officer || "____________________"}
Attachments: Aegis investigation report (${header.trace_id})
`;

  return {
    notice_draft: {
      to: `${vasp} - Nodal/Compliance`,
      subject: `Information/preservation request — ${ref} — ${vasp}`,
      body_markdown: body,
      legal_basis: basis,
      attachments: [`aegis-report-${header.trace_id}.json`],
      editable: true,
    },
    based_on: {
      trace_id: header.trace_id,
      vasp_rank: candidate.rank,
      result_hash: header.result_hash,
    },
  };
}
