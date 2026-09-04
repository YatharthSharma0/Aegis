import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { ErrorState } from "./ErrorState";

it("names the backend-unreachable case explicitly", () => {
  render(
    <ErrorState error={new ApiError("backend_unavailable", "x", 0)} />,
  );
  expect(screen.getByText(/can't reach the aegis backend/i)).toBeInTheDocument();
});

it("shows a not-found message for a 404", () => {
  render(<ErrorState error={new ApiError("not_found", "nope", 404)} />);
  expect(screen.getByText(/does not exist/i)).toBeInTheDocument();
});

it("falls back to a generic message and wires the retry button", () => {
  const onRetry = vi.fn();
  render(<ErrorState error={new Error("boom")} onRetry={onRetry} context="load cases" />);
  expect(screen.getByText(/something went wrong trying to load cases/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /try again/i }));
  expect(onRetry).toHaveBeenCalledOnce();
});
