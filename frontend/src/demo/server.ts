/**
 * The in-browser stand-in for the backend. It takes the same paths, methods and
 * bodies as the real API and answers in the same shapes, including errors, so
 * no screen needs to know which one it is talking to.
 */
import { ApiError } from "../api/client";
import type { SahyogNoticeParams } from "../api/report";
import type {
  AddComplaintRequest,
  CaseOut,
  CaseStatus,
  ComplaintOut,
  CreateCaseRequest,
  MeResponse,
  TraceRequest,
  TraceStatus,
  TraceStatusResponse,
  UpdateCaseRequest,
} from "../api/types";
import { useAuthStore } from "../state/authStore";
import { DEMO_ACCOUNTS } from "./accounts";
import { appendAudit, verifyAudit, type AuditFields } from "./audit";
import { buildNotice } from "./notice";
import { scenarioByKey, scenarioBySeed, type Scenario } from "./scenarios";
import type { DemoComplaint, DemoRun } from "./seed";
import { demoState, saveDemoState } from "./store";

interface DemoRequest {
  method?: string;
  body?: unknown;
}

/** A new trace shows "queued", then "running", before its result appears. */
export const QUEUED_MS = 1500;
export const RUNNING_MS = 4000;

const TOKEN_PREFIX = "demo-token:";
const FAILED_MESSAGE = "chain data provider unavailable (sample failure)";

const notFound = (what: string, id: string) =>
  new ApiError("not_found", `no ${what} with id '${id}'`, 404);
const invalid = (message: string) => new ApiError("invalid_request", message, 400);

const newId = (kind: string) =>
  `demo-${kind}-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

// -- auth -------------------------------------------------------------------

function tokensFor(user: MeResponse) {
  return {
    access_token: `${TOKEN_PREFIX}${user.id}`,
    refresh_token: `${TOKEN_PREFIX}${user.id}`,
    token_type: "bearer",
    role: user.role,
    expires_in: 900,
  };
}

function currentUser(): MeResponse {
  const token = useAuthStore.getState().accessToken;
  const user = DEMO_ACCOUNTS.find((a) => `${TOKEN_PREFIX}${a.id}` === token);
  if (!user) throw new ApiError("unauthenticated", "sign in to continue", 401);
  return user;
}

/** Any email and password work; an `admin…` address gets the admin account. */
function login(body: { email: string }) {
  const admin = body.email.trim().toLowerCase().startsWith("admin");
  const user = DEMO_ACCOUNTS[admin ? 1 : 0];
  audit(user, { action: "auth.login" });
  saveDemoState();
  return tokensFor(user);
}

function audit(user: MeResponse, fields: Partial<AuditFields> & { action: string }) {
  appendAudit(demoState().audit, {
    ts: new Date().toISOString(),
    actor_id: user.id,
    actor_role: user.role,
    trace_id: null,
    case_id: null,
    address: null,
    chain: null,
    detail: null,
    result_hash: null,
    request_id: newId("req"),
    ...fields,
  });
}

// -- traces -----------------------------------------------------------------

function findRun(id: string): DemoRun {
  const run = demoState().runs.find((r) => r.trace_id === id);
  if (!run) throw notFound("trace", id);
  return run;
}

function runStatus(run: DemoRun): TraceStatus {
  const age = Date.now() - run.created_at;
  if (age < QUEUED_MS) return "queued";
  if (age < RUNNING_MS) return "running";
  return run.scenario ? scenarioByKey(run.scenario)!.trace.status : "failed";
}

/** The scenario behind a run, once the run has produced a result. */
function finishedScenario(run: DemoRun): Scenario | null {
  const status = runStatus(run);
  if (status !== "done" && status !== "partial") return null;
  return scenarioByKey(run.scenario!) ?? null;
}

function traceStatus(user: MeResponse, run: DemoRun): TraceStatusResponse {
  const status = runStatus(run);
  const scenario = finishedScenario(run);
  if (!run.settled && status !== "queued" && status !== "running") {
    run.settled = true;
    audit(user, {
      action: status === "failed" ? "trace.failed" : "trace.complete",
      trace_id: run.trace_id,
      case_id: run.case_id,
      result_hash: scenario?.trace.result_hash ?? null,
    });
    saveDemoState();
  }
  const created = new Date(run.created_at).toISOString();
  const terminal = status === "done" || status === "partial" || status === "failed";
  return {
    trace_id: run.trace_id,
    case_id: run.case_id,
    start_address: run.start_address,
    chain: "tron",
    status,
    created_at: created,
    started_at: status === "queued" ? null : created,
    finished_at: terminal ? new Date(run.created_at + RUNNING_MS).toISOString() : null,
    block_heights: scenario?.trace.block_heights ?? {},
    result_hash: scenario?.trace.result_hash ?? null,
    result: scenario?.trace.result ?? null,
    error: status === "failed" ? FAILED_MESSAGE : null,
  };
}

function startTrace(user: MeResponse, body: TraceRequest) {
  if (body.chain !== "tron") throw invalid(`chain ${body.chain} is not supported yet`);
  const scenario = scenarioBySeed(body.address.trim());
  if (!scenario) {
    // Never invent a result for an address we have no data for.
    throw invalid("Demo mode can only trace the sample addresses listed on this page.");
  }
  if (body.case_id) findCase(body.case_id);
  const run: DemoRun = {
    trace_id: newId("trace"),
    case_id: body.case_id ?? null,
    scenario: scenario.key,
    start_address: scenario.seed,
    created_at: Date.now(),
    settled: false,
  };
  demoState().runs.push(run);
  audit(user, {
    action: "trace.start", trace_id: run.trace_id, case_id: run.case_id,
    address: run.start_address, chain: "tron",
  });
  saveDemoState();
  return {
    trace_id: run.trace_id,
    status: "queued",
    stream_url: `/api/v1/trace/${run.trace_id}/stream`,
  };
}

function report(user: MeResponse, run: DemoRun) {
  const scenario = finishedScenario(run);
  if (!scenario) {
    throw new ApiError(
      "trace_not_ready", `trace '${run.trace_id}' is ${runStatus(run)}, not finished`, 409,
    );
  }
  const now = new Date().toISOString();
  const base = scenario.report;
  return {
    ...base,
    header: {
      ...base.header,
      trace_id: run.trace_id,
      case_id: run.case_id,
      generated_at: now,
      generated_by: user.email,
    },
    certification: { ...base.certification, generated_at: now },
    caveats: [
      "SAMPLE: every address, transaction and entity in this report is synthetic.",
      ...base.caveats,
    ],
  };
}

// -- cases ------------------------------------------------------------------

function findCase(id: string): CaseOut {
  const found = demoState().cases.find((c) => c.id === id);
  if (!found) throw notFound("case", id);
  return found;
}

const complaintOut = (c: DemoComplaint): ComplaintOut => ({
  id: c.id,
  source: c.source,
  is_demo: true,
  received_at: c.received_at,
  text_preview: c.text.slice(0, 160),
});

function listCases(user: MeResponse, query: URLSearchParams): CaseOut[] {
  const status = query.get("status");
  return demoState()
    .cases.filter((c) => !status || c.status === status)
    .filter((c) => query.get("mine") !== "true" || c.created_by === user.id)
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, Number(query.get("limit") ?? 100));
}

function caseDetail(id: string) {
  const state = demoState();
  return {
    ...findCase(id),
    complaints: state.complaints.filter((c) => c.case_id === id).map(complaintOut),
    trace_runs: state.runs
      .filter((r) => r.case_id === id)
      .map((r) => ({
        trace_id: r.trace_id,
        status: runStatus(r),
        start_address: r.start_address,
        created_at: new Date(r.created_at).toISOString(),
        result_hash: finishedScenario(r)?.trace.result_hash ?? null,
      })),
  };
}

function createCase(user: MeResponse, body: CreateCaseRequest): CaseOut {
  const refNo = body.ref_no.trim();
  const title = body.title.trim();
  if (!refNo || !title) throw invalid("ref_no and title are required");
  if (demoState().cases.some((c) => c.ref_no === refNo)) {
    throw new ApiError("conflict", `a case with ref_no '${refNo}' already exists`, 409);
  }
  const now = new Date().toISOString();
  const created: CaseOut = {
    id: newId("case"), ref_no: refNo, title, status: "open" satisfies CaseStatus,
    typology_hint: body.typology_hint ?? null, notes: body.notes ?? null,
    created_by: user.id, created_at: now, updated_at: now,
  };
  demoState().cases.push(created);
  audit(user, { action: "case.create", case_id: created.id, detail: { ref_no: refNo } });
  saveDemoState();
  return created;
}

function updateCase(user: MeResponse, id: string, body: UpdateCaseRequest): CaseOut {
  const current = findCase(id);
  current.title = body.title?.trim() || current.title;
  current.status = body.status ?? current.status;
  current.typology_hint = body.typology_hint ?? current.typology_hint;
  current.notes = body.notes ?? current.notes;
  current.updated_at = new Date().toISOString();
  audit(user, { action: "case.update", case_id: id, detail: { status: current.status } });
  saveDemoState();
  return current;
}

function addComplaint(user: MeResponse, caseId: string, body: AddComplaintRequest) {
  findCase(caseId);
  if (!body.is_demo) throw invalid("real complaint text cannot be stored yet");
  if (!body.text.trim()) throw invalid("complaint text is empty");
  const complaint: DemoComplaint = {
    id: newId("complaint"), case_id: caseId, source: body.source ?? "manual",
    text: body.text, received_at: new Date().toISOString(),
  };
  demoState().complaints.push(complaint);
  audit(user, { action: "complaint.attach", case_id: caseId, detail: { source: complaint.source } });
  saveDemoState();
  return complaintOut(complaint);
}

// -- routing ----------------------------------------------------------------

function route(method: string, url: URL, body: unknown): unknown {
  // "/api/v1/<root>/<id>/<action>"
  const [, , root, id, action] = url.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  const key = `${method} ${root}`;

  if (key === "GET health") {
    return { status: "ok", service: "aegis-demo", version: "demo", environment: "demo" };
  }
  if (key === "POST auth" && id === "login") return login(body as { email: string });

  const user = currentUser();

  if (key === "POST auth" && id === "refresh") return tokensFor(user);
  if (key === "GET auth" && id === "me") return user;

  if (root === "cases") {
    if (!id) {
      if (method === "GET") return listCases(user, url.searchParams);
      if (method === "POST") return createCase(user, body as CreateCaseRequest);
    } else if (!action) {
      if (method === "GET") return caseDetail(id);
      if (method === "PATCH") return updateCase(user, id, body as UpdateCaseRequest);
    } else if (action === "complaints" && method === "POST") {
      return addComplaint(user, id, body as AddComplaintRequest);
    }
  }

  if (root === "trace") {
    if (!id && method === "POST") return startTrace(user, body as TraceRequest);
    if (id) {
      const run = findRun(id);
      if (method === "GET" && !action) return traceStatus(user, run);
      if (method === "GET" && action === "graph") {
        const graph = finishedScenario(run)?.graph;
        return { trace_id: id, nodes: graph?.nodes ?? [], edges: graph?.edges ?? [] };
      }
      if (method === "GET" && action === "report") {
        const built = report(user, run);
        audit(user, {
          action: "report.generate", trace_id: id, result_hash: built.header.result_hash,
        });
        saveDemoState();
        return built;
      }
      if (method === "POST" && action === "sahyog-notice") {
        const params = body as SahyogNoticeParams;
        const built = report(user, run);
        const rank = params.vasp_rank ?? 1;
        const candidate = built.vasp_candidates.find((c) => c.rank === rank);
        if (!candidate) throw invalid(`no VASP candidate at rank ${rank}`);
        audit(user, { action: "notice.draft", trace_id: id, detail: { vasp_rank: rank } });
        saveDemoState();
        return buildNotice(built, candidate, params);
      }
    }
  }

  if (key === "GET admin" && id === "audit") {
    if (user.role !== "admin") throw new ApiError("forbidden", "requires role: admin", 403);
    const log = demoState().audit;
    const wanted = url.searchParams.get("action");
    const actor = url.searchParams.get("actor_id");
    return {
      verification: verifyAudit(log),
      entries: log
        .filter((e) => (!wanted || e.action === wanted) && (!actor || e.actor_id === actor))
        .slice()
        .reverse()
        .slice(0, Number(url.searchParams.get("limit") ?? 100)),
    };
  }

  throw new ApiError("not_found", `demo mode has no ${method} ${url.pathname}`, 404);
}

export async function demoRequest(path: string, opts: DemoRequest = {}): Promise<unknown> {
  // A short pause so loading states are visible, as they would be over a network.
  await new Promise((resolve) => setTimeout(resolve, import.meta.env.MODE === "test" ? 0 : 180));
  const result = route(opts.method ?? "GET", new URL(path, "http://demo.local"), opts.body);
  // Hand out copies: callers must not be able to mutate the stored state.
  return structuredClone(result);
}
