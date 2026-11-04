/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DeleteItemButton } from "./DeleteItemButton";

describe("DeleteItemButton", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  function render(onDelete: () => Promise<boolean>) {
    return act(async () => {
      root.render(
        <DeleteItemButton
          label="Delete item Soup"
          dialogTitle="Delete “Soup”?"
          message="This can't be undone."
          confirmLabel="Delete"
          cancelLabel="Cancel"
          errorMessage="Not deleted."
          onDelete={onDelete}
        />,
      );
    });
  }

  const trash = () =>
    container.querySelector<HTMLButtonElement>(
      'button[aria-label="Delete item Soup"]',
    )!;
  const dialog = () => document.querySelector<HTMLElement>('[role="dialog"]');
  const footerButton = (text: string) =>
    Array.from(dialog()!.querySelectorAll<HTMLButtonElement>("button")).find(
      (el) => el.textContent === text,
    )!;

  it("asks before deleting, and does nothing on cancel", async () => {
    const onDelete = vi.fn(async () => true);
    await render(onDelete);
    expect(dialog()).toBeNull();

    await act(async () => trash().click());
    expect(dialog()?.textContent).toContain("Delete “Soup”?");
    await act(async () => footerButton("Cancel").click());
    expect(dialog()).toBeNull();
    expect(onDelete).not.toHaveBeenCalled();
  });

  it("runs the delete on confirm and closes when it succeeds", async () => {
    const onDelete = vi.fn(async () => true);
    await render(onDelete);
    await act(async () => trash().click());
    await act(async () => footerButton("Delete").click());
    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(dialog()).toBeNull();
  });

  it("stays open with the error when the delete fails", async () => {
    await render(async () => false);
    await act(async () => trash().click());
    await act(async () => footerButton("Delete").click());
    expect(dialog()).not.toBeNull();
    expect(dialog()?.querySelector('[role="alert"]')?.textContent).toBe(
      "Not deleted.",
    );
  });
});
