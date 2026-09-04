import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../test/renderWithProviders";
import { CasesPage } from "./CasesPage";

const listCases = vi.fn();
const createCase = vi.fn();

vi.mock("../api/cases", () => ({
  listCases: (...a: unknown[]) => listCases(...a),
  createCase: (...a: unknown[]) => createCase(...a),
  getCase: vi.fn(),
  updateCase: vi.fn(),
  addComplaint: vi.fn(),
}));

const CASE = {
  id: "c1",
  ref_no: "FIR 1/2026",
  title: "USDT drain",
  status: "open",
  typology_hint: null,
  notes: null,
  created_by: "officer",
  created_at: "2026-09-01T10:00:00Z",
  updated_at: "2026-09-02T10:00:00Z",
};

beforeEach(() => {
  listCases.mockReset();
  createCase.mockReset();
});

it("lists cases from the API", async () => {
  listCases.mockResolvedValue([CASE]);
  renderWithProviders(<CasesPage />);
  expect(await screen.findByText("USDT drain")).toBeInTheDocument();
  expect(screen.getByText(/FIR 1\/2026/)).toBeInTheDocument();
});

it("shows an empty state when there are no cases", async () => {
  listCases.mockResolvedValue([]);
  renderWithProviders(<CasesPage />);
  expect(
    await screen.findByText(/no cases match this filter/i),
  ).toBeInTheDocument();
});

it("refetches with a status filter when a chip is chosen", async () => {
  listCases.mockResolvedValue([]);
  renderWithProviders(<CasesPage />);
  await screen.findByText(/no cases match/i);

  fireEvent.click(await screen.findByRole("button", { name: "Closed" }));

  await waitFor(() =>
    expect(listCases.mock.calls.at(-1)?.[0]).toEqual({ status: "closed" }),
  );
});
