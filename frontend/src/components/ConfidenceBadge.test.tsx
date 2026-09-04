import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { confidenceBand } from "../features/trace/confidence";
import { ConfidenceBadge } from "./ConfidenceBadge";

it("bands confidence values", () => {
  expect(confidenceBand(0.9)).toBe("high");
  expect(confidenceBand(0.5)).toBe("medium");
  expect(confidenceBand(0.1)).toBe("low");
});

it("renders a word and a percentage, not colour alone", () => {
  render(<ConfidenceBadge confidence="0.82" />);
  expect(screen.getByText(/high confidence · 82%/i)).toBeInTheDocument();
});

it("clamps out-of-range and non-numeric input", () => {
  const { rerender } = render(<ConfidenceBadge confidence="5" />);
  expect(screen.getByText(/100%/)).toBeInTheDocument();
  rerender(<ConfidenceBadge confidence="not-a-number" />);
  expect(screen.getByText(/low confidence · 0%/i)).toBeInTheDocument();
});
