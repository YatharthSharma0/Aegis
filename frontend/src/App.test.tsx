import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import App from "./App";
import { useAuthStore } from "./state/authStore";

beforeEach(() => {
  useAuthStore.getState().clear();
});

it("shows the landing page to an unauthenticated visitor at the root", () => {
  window.history.pushState({}, "", "/");
  render(<App />);
  expect(
    screen.getByRole("heading", { name: /follow the money, on-chain/i }),
  ).toBeInTheDocument();
});

it("redirects an unauthenticated visitor away from a protected route", () => {
  window.history.pushState({}, "", "/cases");
  render(<App />);
  expect(screen.getByText(/investigator sign-in/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
});

it("shows the dashboard once a session exists", () => {
  useAuthStore.getState().setSession({
    accessToken: "test-access",
    refreshToken: "test-refresh",
    role: "investigator",
    email: "officer@i4c.gov.in",
  });
  window.history.pushState({}, "", "/");
  render(<App />);
  expect(
    screen.getByRole("heading", { name: "Dashboard" }),
  ).toBeInTheDocument();
});
