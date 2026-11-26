import { fireEvent, screen, waitFor } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { renderWithProviders } from "../test/renderWithProviders";
import { CaseDetailPage } from "./CaseDetailPage";

const addComplaint = vi.fn();

vi.mock("../api/cases", () => ({
  getCase: () =>
    Promise.resolve({
      id: "c1", ref_no: "REF-1", title: "A case", status: "open",
      typology_hint: null, notes: null, created_by: null,
      created_at: "2026-09-01T00:00:00Z", updated_at: "2026-09-01T00:00:00Z",
      complaints: [], trace_runs: [],
    }),
  addComplaint: (...a: unknown[]) => addComplaint(...a),
}));

async function renderAndType() {
  renderWithProviders(
    <Routes>
      <Route path="/cases/:id" element={<CaseDetailPage />} />
    </Routes>,
    { route: "/cases/c1" },
  );
  fireEvent.change(await screen.findByLabelText(/add complaint text/i), {
    target: { value: "A made-up complaint" },
  });
}

beforeEach(() => addComplaint.mockReset());

it("attaches text only once the officer declares it fictional", async () => {
  addComplaint.mockResolvedValue({});
  await renderAndType();
  const attach = screen.getByRole("button", { name: "Attach" });
  expect(attach).toBeDisabled();

  fireEvent.click(screen.getByRole("checkbox", { name: /fictional/i }));
  fireEvent.click(attach);

  await waitFor(() =>
    expect(addComplaint).toHaveBeenCalledWith("c1", {
      text: "A made-up complaint", source: "manual", is_demo: true,
    }),
  );
});

it("shows the backend's reason when it refuses the complaint", async () => {
  addComplaint.mockRejectedValue(
    new ApiError("invalid_request", "complaint text is empty", 400),
  );
  await renderAndType();
  fireEvent.click(screen.getByRole("checkbox", { name: /fictional/i }));
  fireEvent.click(screen.getByRole("button", { name: "Attach" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("complaint text is empty");
});
