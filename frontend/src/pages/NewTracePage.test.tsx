import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
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

it("surfaces the backend's rejection reason inline — e.g. an unsupported chain", async () => {
  startTrace.mockRejectedValue(
    new ApiError(
      "invalid_request",
      "chain ethereum is not supported yet",
      400,
      { supported: ["tron"] },
    ),
  );
  renderWithProviders(<NewTracePage />, { route: "/trace/new" });

  fireEvent.change(screen.getByLabelText(/address under investigation/i), {
    target: { value: "0x0000000000000000000000000000000000dEaD" },
  });
  fireEvent.change(screen.getByLabelText(/^chain$/i), {
    target: { value: "ethereum" },
  });
  fireEvent.click(screen.getByRole("button", { name: /start trace/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    /chain ethereum is not supported yet/i,
  );
  // A rejected trace must never silently navigate away as if it started.
  expect(navigate).not.toHaveBeenCalled();
});
