import { screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import type { AuditResponse } from "../api/types";
import { renderWithProviders } from "../test/renderWithProviders";
import { AdminAuditPage } from "./AdminAuditPage";

const getAudit = vi.fn();

vi.mock("../api/system", () => ({
  getAudit: (...a: unknown[]) => getAudit(...a),
  getHealth: vi.fn(),
}));

const base: AuditResponse = {
  verification: { ok: true, checked: 2, broken_at_seq: null, reason: null },
  entries: [
    {
      seq: 1,
      ts: "2026-09-03T09:00:00Z",
      actor_id: "officer",
      actor_role: "investigator",
      action: "trace.start",
      trace_id: "tr-1",
      case_id: null,
      address: null,
      chain: null,
      detail: null,
      result_hash: null,
      request_id: "req-1",
      prev_row_hash: "0".repeat(64),
      row_hash: "a".repeat(64),
    },
  ],
};

beforeEach(() => getAudit.mockReset());

it("shows the chain-intact banner and the entries", async () => {
  getAudit.mockResolvedValue(base);
  renderWithProviders(<AdminAuditPage />);
  expect(await screen.findByText(/chain intact/i)).toBeInTheDocument();
  expect(screen.getByText("trace.start")).toBeInTheDocument();
});

it("flags a broken chain", async () => {
  getAudit.mockResolvedValue({
    ...base,
    verification: {
      ok: false,
      checked: 5,
      broken_at_seq: 3,
      reason: "row hash mismatch",
    },
  });
  renderWithProviders(<AdminAuditPage />);
  expect(await screen.findByText(/chain broken at seq 3/i)).toBeInTheDocument();
});
