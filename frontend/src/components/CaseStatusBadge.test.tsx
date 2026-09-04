import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { CaseStatusBadge } from "./CaseStatusBadge";

it("renders a word for each known status, not colour alone", () => {
  const { rerender } = render(<CaseStatusBadge status="open" />);
  expect(screen.getByText("Open")).toBeInTheDocument();
  rerender(<CaseStatusBadge status="in_progress" />);
  expect(screen.getByText("In progress")).toBeInTheDocument();
  rerender(<CaseStatusBadge status="closed" />);
  expect(screen.getByText("Closed")).toBeInTheDocument();
});

it("falls back to the raw value for an unknown status", () => {
  render(<CaseStatusBadge status="archived" />);
  expect(screen.getByText("archived")).toBeInTheDocument();
});
