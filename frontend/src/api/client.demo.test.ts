import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

it("answers from sample data without touching the network in demo mode", async () => {
  vi.stubEnv("VITE_DATA_MODE", "demo");
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  vi.resetModules();
  const { get } = await import("./client");

  await expect(get("/api/v1/health")).resolves.toMatchObject({ status: "ok" });
  expect(fetch).not.toHaveBeenCalled();
});
