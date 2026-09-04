import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import type { InvestigationReport } from "../api/report";
import { renderWithProviders } from "../test/renderWithProviders";
import { ReportPage } from "./ReportPage";

const getReport = vi.fn();
const createSahyogNotice = vi.fn();

vi.mock("../api/report", () => ({
  getReport: (...a: unknown[]) => getReport(...a),
  createSahyogNotice: (...a: unknown[]) => createSahyogNotice(...a),
}));

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useParams: () => ({ id: "tr-1" }) };
});

const REPORT: InvestigationReport = {
  report_type: "aegis.investigation_report.v1",
  header: {
    trace_id: "tr-1",
    case_id: "FIR-1",
    reported_address: "TVictimAddr000000000000000000000000",
    chain: "tron",
    status: "done",
    partial_reason: null,
    generated_at: "2026-09-03T09:00:00Z",
    generated_by: "officer@i4c.gov.in",
    block_heights: { tron: 60000000 },
    result_hash: "a".repeat(64),
  },
  officer_summary: "Funds traced to Binance deposit address.",
  vasp_candidates: [
    {
      rank: 1,
      tier: "dataset_confirmed",
      verified: true,
      name: "Binance",
      label: null,
      source: "aegis_demo_pack",
      confidence: "0.83",
      confidence_formula: {
        terms: { source: "1", directness: "0.5" },
        weights: { source: "0.45", directness: "0.15" },
        raw_score: "0.83",
        score: "0.83",
      },
      deposit_address: "TDepositAddr00000000000000000000000",
      hops_from_seed: 3,
      reaching_paths: 2,
      signals: ["known_deposit"],
      evidence: [],
    },
  ],
  fund_flow: [],
  typologies: [],
  trail_events: [],
  data_sources: [],
  certification: {
    statement: "Deterministic.",
    method: "haircut",
    reproducibility_anchor: "a".repeat(64),
    generated_at: "2026-09-03T09:00:00Z",
  },
  caveats: ["Assistive only."],
};

beforeEach(() => {
  getReport.mockReset();
  createSahyogNotice.mockReset();
});

it("renders the report headline and attribution", async () => {
  getReport.mockResolvedValue(REPORT);
  renderWithProviders(<ReportPage />);
  expect(await screen.findByText(/investigation report/i)).toBeInTheDocument();
  expect(
    screen.getByText(/funds traced to binance deposit address/i),
  ).toBeInTheDocument();
  expect(screen.getByText(/#1 Binance/)).toBeInTheDocument();
});

it("generates an editable SAHYOG notice draft", async () => {
  getReport.mockResolvedValue(REPORT);
  createSahyogNotice.mockResolvedValue({
    notice_draft: {
      to: "Binance - Nodal/Compliance",
      subject: "Information/preservation request — FIR-1 — Binance",
      body_markdown: "To: Binance\n\n1. This office is investigating…",
      legal_basis: "IT Act s.79(3)(b)",
      attachments: ["aegis-report-tr-1.json"],
      editable: true,
    },
    based_on: { trace_id: "tr-1", vasp_rank: 1, result_hash: "a".repeat(64) },
  });

  renderWithProviders(<ReportPage />);
  fireEvent.click(await screen.findByRole("button", { name: /generate draft/i }));

  const body = await screen.findByLabelText("Notice body");
  await waitFor(() =>
    expect((body as HTMLTextAreaElement).value).toMatch(
      /this office is investigating/i,
    ),
  );
});
