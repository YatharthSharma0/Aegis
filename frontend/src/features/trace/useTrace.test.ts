import { expect, it } from "vitest";

import { isTerminal, pollInterval } from "./useTrace";

it("keeps polling while the run is active", () => {
  expect(pollInterval("queued")).toBe(2000);
  expect(pollInterval("running")).toBe(2000);
  expect(pollInterval(undefined)).toBe(2000);
});

it("stops polling once the run reaches a terminal state", () => {
  expect(pollInterval("done")).toBe(false);
  expect(pollInterval("partial")).toBe(false);
  expect(pollInterval("failed")).toBe(false);
});

it("classifies terminal states", () => {
  expect(isTerminal("done")).toBe(true);
  expect(isTerminal("running")).toBe(false);
  expect(isTerminal(undefined)).toBe(false);
});
