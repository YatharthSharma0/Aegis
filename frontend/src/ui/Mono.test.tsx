import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { Mono } from "./Mono";

const ADDR = "TJ1a2b3c4d5e6f7g8h9i0jKLMNOPQRSTUV";

beforeEach(() => {
  Object.assign(navigator, {
    clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

it("middle-truncates a long value but keeps the full value available", () => {
  render(<Mono value={ADDR} />);
  const btn = screen.getByRole("button");
  expect(btn).toHaveAttribute("title", ADDR);
  expect(btn).toHaveTextContent(`${ADDR.slice(0, 8)}…${ADDR.slice(-6)}`);
  expect(btn).not.toHaveTextContent(ADDR);
});

it("shows short values verbatim", () => {
  render(<Mono value="TShort123" />);
  expect(screen.getByRole("button")).toHaveTextContent("TShort123");
});

it("copies the full value on click", async () => {
  render(<Mono value={ADDR} />);
  fireEvent.click(screen.getByRole("button"));
  expect(navigator.clipboard.writeText).toHaveBeenCalledWith(ADDR);
  expect(await screen.findByLabelText("copied")).toBeInTheDocument();
});
