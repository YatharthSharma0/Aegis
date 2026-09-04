import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../test/renderWithProviders";
import { AppShell } from "./AppShell";

const useHealth = vi.fn();

vi.mock("../features/system/useHealth", () => ({
  useHealth: () => useHealth(),
}));

vi.mock("./useAuth", () => ({
  useAuth: () => ({
    email: "officer@i4c.gov.in",
    role: "officer",
    logout: vi.fn(),
  }),
}));

it("shows no banner while the backend is reachable", () => {
  useHealth.mockReturnValue({ offline: false });
  renderWithProviders(
    <AppShell>
      <div>content</div>
    </AppShell>,
  );
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("shows a clear, retrying banner when the backend is unreachable — never a silent failure", () => {
  useHealth.mockReturnValue({ offline: true });
  renderWithProviders(
    <AppShell>
      <div>content</div>
    </AppShell>,
  );
  expect(screen.getByRole("alert")).toHaveTextContent(/backend unreachable/i);
  // The page underneath keeps rendering — this is a banner, not a blocking
  // full-page error state (last-known data stays visible while retrying).
  expect(screen.getByText("content")).toBeInTheDocument();
});
