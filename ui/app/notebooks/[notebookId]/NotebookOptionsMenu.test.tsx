/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NotebookOptionsMenu } from "./NotebookOptionsMenu";

describe("NotebookOptionsMenu", () => {
  let container: HTMLDivElement;
  let root: Root;
  const onRename = vi.fn();
  const onDelete = vi.fn();

  beforeEach(() => {
    onRename.mockReset();
    onDelete.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    act(() =>
      root.render(<NotebookOptionsMenu locale="en" onRename={onRename} onDelete={onDelete} />),
    );
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  const trigger = () =>
    container.querySelector('button[aria-label="Notebook options"]') as HTMLButtonElement;
  const items = () => Array.from(container.querySelectorAll<HTMLElement>('[role="menuitem"]'));

  function openMenu() {
    act(() => trigger().click());
  }

  function press(key: string) {
    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    });
  }

  it("offers Rename and Delete once opened", () => {
    expect(items()).toEqual([]);
    openMenu();
    expect(items().map((el) => el.textContent)).toEqual(["Rename", "Delete"]);
  });

  it("calls the chosen action and closes", () => {
    openMenu();
    act(() => items()[1].click());
    expect(onDelete).toHaveBeenCalled();
    expect(onRename).not.toHaveBeenCalled();
    expect(items()).toEqual([]);
  });

  it("moves with the arrows, wrapping round", () => {
    openMenu();
    press("ArrowDown");
    expect(document.activeElement?.textContent).toBe("Rename");
    press("ArrowDown");
    expect(document.activeElement?.textContent).toBe("Delete");
    press("ArrowDown");
    expect(document.activeElement?.textContent).toBe("Rename");
    press("ArrowUp");
    expect(document.activeElement?.textContent).toBe("Delete");
  });

  it("closes on Escape and gives focus back to the button", () => {
    openMenu();
    press("ArrowDown");
    press("Escape");
    expect(items()).toEqual([]);
    expect(document.activeElement).toBe(trigger());
  });
});
