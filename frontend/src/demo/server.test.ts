import { beforeEach, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import type {
  AuditResponse,
  CaseDetailOut,
  CaseOut,
  TraceAccepted,
  TraceGraphResponse,
  TraceStatusResponse,
} from "../api/types";
import { useAuthStore } from "../state/authStore";
import { DEMO_ACCOUNTS, DEMO_PASSWORD } from "./accounts";
import { SCENARIOS } from "./scenarios";
import { demoRequest, QUEUED_MS, RUNNING_MS } from "./server";
import { sha256Hex } from "./sha256";
import { demoState, resetDemoState } from "./store";

const call = <T>(method: string, path: string, body?: unknown) =>
  demoRequest(path, { method, body }) as Promise<T>;

function signIn(email: string = DEMO_ACCOUNTS[0].email) {
  return call<{ access_token: string; refresh_token: string; role: "officer" }>(
    "POST", "/api/v1/auth/login", { email, password: DEMO_PASSWORD },
  ).then((t) =>
    useAuthStore.getState().setSession({
      accessToken: t.access_token, refreshToken: t.refresh_token, role: t.role,
    }),
  );
}

beforeEach(async () => {
  vi.useRealTimers();
  useAuthStore.getState().clear();
  resetDemoState();
  await signIn();
});

it("hashes with real SHA-256, including multi-block and non-ASCII input", () => {
  expect(sha256Hex("abc")).toBe(
    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
  );
  expect(sha256Hex("")).toBe(
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  );
  expect(sha256Hex("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq")).toBe(
    "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
  );
  expect(sha256Hex("é—")).toHaveLength(64);
});

it("rejects requests without a session", async () => {
  useAuthStore.getState().clear();
  await expect(call("GET", "/api/v1/cases")).rejects.toMatchObject({ status: 401 });
});

it("serves seeded cases whose trace runs all open", async () => {
  const cases = await call<CaseOut[]>("GET", "/api/v1/cases");
  expect(cases.length).toBeGreaterThanOrEqual(10);
  for (const c of cases) {
    const detail = await call<CaseDetailOut>("GET", `/api/v1/cases/${c.id}`);
    for (const run of detail.trace_runs) {
      const trace = await call<TraceStatusResponse>("GET", `/api/v1/trace/${run.trace_id}`);
      expect(trace.status).toBe(run.status);
      if (trace.status !== "failed") {
        await call("GET", `/api/v1/trace/${run.trace_id}/report`);
      }
    }
  }
});

it("has a consistent graph for every scenario", () => {
  for (const s of SCENARIOS) {
    const ids = new Set(s.graph.nodes.map((n) => n.id));
    expect(ids.has(s.seed)).toBe(true);
    for (const e of s.graph.edges) {
      expect(ids.has(e.from) && ids.has(e.to)).toBe(true);
    }
  }
});

it("creates and updates a case, refusing a duplicate reference", async () => {
  const body = { ref_no: "SAMPLE/NEW/1", title: "New one" };
  const created = await call<CaseOut>("POST", "/api/v1/cases", body);
  await expect(call("POST", "/api/v1/cases", body)).rejects.toMatchObject({ status: 409 });
  await call("PATCH", `/api/v1/cases/${created.id}`, { status: "closed" });
  await call("POST", `/api/v1/cases/${created.id}/complaints`, {
    source: "manual", text: "fictional", is_demo: false,
  });
  const detail = await call<CaseDetailOut>("GET", `/api/v1/cases/${created.id}`);
  expect(detail.status).toBe("closed");
  expect(detail.complaints).toHaveLength(1);
});

it("moves a new trace from queued to running to done", async () => {
  vi.useFakeTimers({ toFake: ["Date"] });
  const start = Date.now();
  const { trace_id } = await call<TraceAccepted>("POST", "/api/v1/trace", {
    address: SCENARIOS[0].seed, chain: "tron",
  });
  const read = () => call<TraceStatusResponse>("GET", `/api/v1/trace/${trace_id}`);

  expect((await read()).status).toBe("queued");
  await expect(call("GET", `/api/v1/trace/${trace_id}/report`)).rejects.toMatchObject({
    status: 409,
  });
  vi.setSystemTime(start + QUEUED_MS + 1);
  expect((await read()).status).toBe("running");
  vi.setSystemTime(start + RUNNING_MS + 1);
  expect((await read()).status).toBe("done");

  const graph = await call<TraceGraphResponse>("GET", `/api/v1/trace/${trace_id}/graph`);
  expect(graph.edges.length).toBeGreaterThan(0);
});

it("refuses to invent a result for an unknown address or chain", async () => {
  for (const body of [
    { address: "TUnknown", chain: "tron" },
    { address: SCENARIOS[0].seed, chain: "ethereum" },
  ]) {
    await expect(call("POST", "/api/v1/trace", body)).rejects.toBeInstanceOf(ApiError);
  }
});

it("drafts a notice that is clearly marked as sample data", async () => {
  const draft = await call<{ notice_draft: { body_markdown: string; to: string } }>(
    "POST", "/api/v1/trace/demo-investment/sahyog-notice", { vasp_rank: 1 },
  );
  expect(draft.notice_draft.to).toContain("SampleCoin Exchange");
  expect(draft.notice_draft.body_markdown).toContain("NOT FOR ISSUE");
  expect(draft.notice_draft.body_markdown).toContain("23200.000000 USDT");
});

it("keeps the audit log admin-only, and detects tampering", async () => {
  await expect(call("GET", "/api/v1/admin/audit")).rejects.toMatchObject({ status: 403 });
  await signIn(DEMO_ACCOUNTS[1].email);
  const clean = await call<AuditResponse>("GET", "/api/v1/admin/audit?limit=500");
  expect(clean.verification.ok).toBe(true);
  expect(clean.entries.length).toBeGreaterThan(20);

  demoState().audit[3].action = "tampered";
  const broken = await call<AuditResponse>("GET", "/api/v1/admin/audit");
  expect(broken.verification).toMatchObject({ ok: false, broken_at_seq: 4 });
});
