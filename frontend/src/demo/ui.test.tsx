/** Click through the app in demo mode, with `fetch` forbidden. */
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

it("signs in, lists sample cases and traces a sample address without a backend", async () => {
  vi.stubEnv("VITE_DATA_MODE", "demo");
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  vi.resetModules();
  const { default: App } = await import("../App");
  const { SCENARIOS } = await import("./scenarios");

  window.history.pushState({}, "", "/login");
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: /investigating officer/i }));

  expect(await screen.findByText(/digital-arrest call/i)).toBeInTheDocument();
  expect(screen.getByText("Demo data")).toBeInTheDocument();

  fireEvent.click(screen.getAllByRole("link", { name: "New trace" })[0]);
  fireEvent.click(await screen.findByRole("button", { name: /fake investment platform/i }));
  expect(screen.getByLabelText(/address under investigation/i)).toHaveValue(
    SCENARIOS.find((s) => s.key === "investment")!.seed,
  );
  fireEvent.click(screen.getByRole("button", { name: "Start trace" }));

  expect(await screen.findByText(/queued — waiting/i)).toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
});
