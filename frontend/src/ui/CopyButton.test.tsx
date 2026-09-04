import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { CopyButton } from "./CopyButton";

beforeEach(() => {
  Object.assign(navigator, {
    clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

it("writes the value to the clipboard and confirms", async () => {
  render(<CopyButton value="notice text" label="Copy notice" />);
  const btn = screen.getByRole("button", { name: "Copy notice" });
  fireEvent.click(btn);
  expect(navigator.clipboard.writeText).toHaveBeenCalledWith("notice text");
  expect(await screen.findByText("Copied")).toBeInTheDocument();
});
