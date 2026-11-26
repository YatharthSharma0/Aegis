/** The starting contents of the demo "database": fictional cases and history. */
import type { AuditEntryOut, CaseOut, CaseStatus, ComplaintSource } from "../api/types";
import { appendAudit, type AuditFields } from "./audit";
import { scenarioByKey } from "./scenarios";

export interface DemoComplaint {
  id: string;
  case_id: string;
  source: ComplaintSource;
  text: string;
  received_at: string;
}

export interface DemoRun {
  trace_id: string;
  case_id: string | null;
  /** `null` marks a run that failed and has no result. */
  scenario: string | null;
  start_address: string;
  /** Epoch ms. The visible status is derived from the run's age. */
  created_at: number;
  /** Whether the completion has been written to the audit log. */
  settled: boolean;
}

export interface DemoState {
  cases: CaseOut[];
  complaints: DemoComplaint[];
  runs: DemoRun[];
  audit: AuditEntryOut[];
}

interface SeedCase {
  title: string;
  status: CaseStatus;
  /** Days before "now" the case was opened. */
  age: number;
  typology: string | null;
  notes?: string;
  source: ComplaintSource;
  complaint: string;
  /** Scenario keys traced under this case; "failed" seeds a failed run. */
  runs: string[];
}

const SEED_CASES: SeedCase[] = [
  {
    title: "Part-time task scam — USDT collected in stages", status: "in_progress", age: 2,
    typology: "task scam", source: "ncrp",
    notes: "Complainant retained chat screenshots. Preservation request under review.",
    complaint: "I was added to a group offering paid rating tasks. After two small payouts I was asked to deposit USDT to unlock higher tasks. I sent 1,499.5 USDT and the group then removed me.",
    runs: ["task_scam"],
  },
  {
    title: "Fake investment platform — withdrawals blocked", status: "in_progress", age: 3,
    typology: "investment fraud", source: "ncrp",
    complaint: "A trading app showed my balance doubling. When I tried to withdraw, support demanded a 30% tax first. I had already transferred 25,000 USDT to the address they gave me.",
    runs: ["investment"],
  },
  {
    title: "Digital-arrest call — forced transfer", status: "open", age: 1,
    typology: "digital arrest", source: "1930",
    notes: "Victim was kept on a video call for several hours. Treat as priority.",
    complaint: "Callers posing as enforcement officers said my identity was used in a crime and kept me on video. I was told to move 48,000 USDT to a 'verification account' to avoid arrest.",
    runs: ["digital_arrest"],
  },
  {
    title: "Instant-loan app extortion", status: "open", age: 4,
    typology: "loan-app extortion", source: "1930",
    complaint: "After a small loan the app operators threatened to message my contacts. I paid 4,200 USDT to the wallet they sent.",
    runs: ["heuristic"],
  },
  {
    title: "Phishing approval — wallet drained", status: "in_progress", age: 6,
    typology: "phishing", source: "ncrp",
    complaint: "I connected my wallet to a site that looked like an airdrop page. Minutes later 18,500 USDT left the wallet without my action.",
    runs: ["bridge"],
  },
  {
    title: "P2P merchant sold non-existent USDT", status: "open", age: 8,
    typology: "P2P fraud", source: "manual",
    complaint: "I paid a peer-to-peer seller 9,600 USDT as an escrow deposit. The seller stopped responding and the listing disappeared.",
    runs: ["conflict"],
  },
  {
    title: "Ransom demand after account takeover", status: "open", age: 9,
    typology: "extortion", source: "manual",
    notes: "Funds appear not to have moved onward. Re-check periodically.",
    complaint: "Our small firm's mailbox was taken over. We paid 52,000 USDT after a threat to publish client files.",
    runs: ["watchlist"],
  },
  {
    title: "Layered transfers from matrimonial-site contact", status: "in_progress", age: 12,
    typology: "romance scam", source: "ncrp",
    complaint: "Someone I met on a matrimonial site persuaded me to invest in a crypto pool. I transferred 7,400 USDT and the profile was deleted.",
    runs: ["partial"],
  },
  {
    title: "Fake customer-care number — remote access", status: "open", age: 13,
    typology: "impersonation", source: "1930",
    complaint: "I searched online for support, installed a remote-access app as instructed and found my exchange balance gone.",
    runs: ["failed"],
  },
  {
    title: "Work-from-home deposit fraud", status: "closed", age: 27,
    typology: "task scam", source: "ncrp",
    notes: "Closed after the receiving platform acknowledged the preservation request (sample narrative).",
    complaint: "I was promised daily earnings for liking videos, then asked to pay a refundable deposit in USDT.",
    runs: ["task_scam"],
  },
  {
    title: "Duplicate complaint — investment group", status: "closed", age: 34,
    typology: "investment fraud", source: "manual",
    notes: "Merged with the primary investment-platform case.",
    complaint: "Second family member reporting the same trading app and receiving wallet.",
    runs: ["investment"],
  },
  {
    title: "Courier-parcel impersonation call", status: "open", age: 0,
    typology: "digital arrest", source: "1930",
    complaint: "A caller said a parcel in my name held contraband and transferred me to a fake officer. Wallet details are still being collected.",
    runs: [],
  },
];

const OFFICER = "demo-officer";
const MINUTE = 60_000;
const DAY = 24 * 60 * MINUTE;

export function seedState(now: number = Date.now()): DemoState {
  const state: DemoState = { cases: [], complaints: [], runs: [], audit: [] };
  const events: Array<{ at: number; fields: Partial<AuditFields> & { action: string } }> = [];

  SEED_CASES.forEach((c, i) => {
    const n = String(i + 1).padStart(2, "0");
    const id = `demo-case-${n}`;
    const opened = now - c.age * DAY - (i + 1) * 37 * MINUTE;
    const iso = (offset: number) => new Date(opened + offset).toISOString();
    const refNo = `SAMPLE/CYB/2026/${String(140 + i * 7).padStart(4, "0")}`;

    state.cases.push({
      id, ref_no: refNo, title: c.title, status: c.status,
      typology_hint: c.typology, notes: c.notes ?? null, created_by: OFFICER,
      created_at: iso(0), updated_at: iso((i % 4) * MINUTE + 5 * MINUTE),
    });
    events.push({ at: opened, fields: { action: "case.create", case_id: id, detail: { ref_no: refNo } } });

    state.complaints.push({
      id: `demo-complaint-${n}`, case_id: id, source: c.source,
      text: c.complaint, received_at: iso(MINUTE),
    });
    events.push({ at: opened + MINUTE, fields: { action: "complaint.attach", case_id: id, detail: { source: c.source } } });

    c.runs.forEach((key, j) => {
      const scenario = scenarioByKey(key);
      // The primary case for a scenario gets the readable id.
      const taken = state.runs.some((r) => r.trace_id === `demo-${key}`);
      const traceId = taken ? `demo-${key}-${n}` : `demo-${key}`;
      const at = opened + (2 + j) * MINUTE;
      const address = scenario?.seed ?? scenarioByKey("task_scam")!.seed;
      state.runs.push({
        trace_id: traceId, case_id: id, scenario: scenario?.key ?? null,
        start_address: address, created_at: at, settled: true,
      });
      const base = { trace_id: traceId, case_id: id };
      events.push({ at, fields: { ...base, action: "trace.start", address, chain: "tron" } });
      if (scenario) {
        const hash = scenario.trace.result_hash;
        events.push({ at: at + 4000, fields: { ...base, action: "trace.complete", result_hash: hash } });
        if (c.status !== "open") {
          events.push({ at: at + 2 * MINUTE, fields: { ...base, action: "report.generate", result_hash: hash } });
        }
        if (c.status === "closed") {
          events.push({ at: at + 3 * MINUTE, fields: { ...base, action: "notice.draft", detail: { vasp_rank: 1 } } });
        }
      } else {
        events.push({ at: at + 4000, fields: { ...base, action: "trace.failed" } });
      }
    });
  });

  events
    .sort((a, b) => a.at - b.at)
    .forEach(({ at, fields }, i) => {
      appendAudit(state.audit, {
        actor_id: OFFICER, actor_role: "officer", trace_id: null, case_id: null,
        address: null, chain: null, detail: null, result_hash: null,
        request_id: `demo-req-${i + 1}`, ...fields, ts: new Date(at).toISOString(),
      });
    });

  return state;
}
