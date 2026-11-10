import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { ErrorBoundary } from "@/components/ErrorBoundary";

function Broken(): never {
  throw new Error("render failure");
}

test("replaces a crashed subtree with an accessible recovery message", () => {
  vi.spyOn(console, "error").mockImplementation(() => undefined);
  render(
    <ErrorBoundary>
      <Broken />
    </ErrorBoundary>,
  );
  expect(screen.getByRole("alert").textContent).toBe(
    "Something went wrong. Reload the page to try again.",
  );
});
