import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../test/renderWithProviders";
import { NewTracePage } from "./NewTracePage";

const startTrace = vi.fn();
const navigate = vi.fn();

vi.mock("../api/trace", () => ({
  startTrace: (...a: unknown[]) => startTrace(...a),
}));

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => navigate };
});

beforeEach(() => {
  startTrace.mockReset();
  navigate.mockReset();
});

it("starts a trace and navigates to its result page", async () => {
  startTrace.mockResolvedValue({ trace_id: "abc123", status: "queued" });
  renderWithProviders(<NewTracePage />, { route: "/trace/new?case=FIR-9" });

  fireEvent.change(screen.getByLabelText(/address under investigation/i), {
    target: { value: "TXYZaddr0000000000000000000000000000" },
  });
  fireEvent.click(screen.getByRole("button", { name: /start trace/i }));

  await waitFor(() => expect(startTrace).toHaveBeenCalledOnce());
  expect(startTrace.mock.calls[0][0]).toMatchObject({
    address: "TXYZaddr0000000000000000000000000000",
    chain: "tron",
    case_id: "FIR-9",
  });
  await waitFor(() => expect(navigate).toHaveBeenCalledWith("/trace/abc123"));
});

it("keeps the submit button disabled until an address is entered", () => {
  renderWithProviders(<NewTracePage />, { route: "/trace/new" });
  expect(screen.getByRole("button", { name: /start trace/i })).toBeDisabled();
});
