import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import App from "./App";
import { useAuthStore } from "./state/authStore";

beforeEach(() => {
  useAuthStore.getState().clear();
});

it("redirects an unauthenticated visitor to the sign-in screen", () => {
  window.history.pushState({}, "", "/");
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
