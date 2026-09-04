import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { Button } from "./Button";

it("marks itself busy and blocks clicks while loading", () => {
  const onClick = vi.fn();
  render(
    <Button loading onClick={onClick}>
      Save
    </Button>,
  );
  const btn = screen.getByRole("button", { name: "Save" });
  expect(btn).toBeDisabled();
  expect(btn).toHaveAttribute("aria-busy", "true");
  fireEvent.click(btn);
  expect(onClick).not.toHaveBeenCalled();
});

it("fires onClick when idle", () => {
  const onClick = vi.fn();
  render(<Button onClick={onClick}>Go</Button>);
  fireEvent.click(screen.getByRole("button", { name: "Go" }));
  expect(onClick).toHaveBeenCalledOnce();
});
