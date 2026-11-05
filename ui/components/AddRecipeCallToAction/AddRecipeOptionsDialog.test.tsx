/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AddRecipeOptionsDialog } from "./AddRecipeOptionsDialog";

let container: HTMLDivElement;
let root: Root;

function labels(): string[] {
  return Array.from(document.querySelectorAll("[role='list'] button")).map(
    (el) => el.querySelector("span")?.textContent ?? "",
  );
}

function render(props: Partial<Parameters<typeof AddRecipeOptionsDialog>[0]> = {}) {
  act(() => {
    root.render(
      <AddRecipeOptionsDialog
        open
        onClose={vi.fn()}
        onChooseUrl={vi.fn()}
        onChooseText={vi.fn()}
        onChooseManual={vi.fn()}
        {...props}
      />,
    );
  });
}

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

describe("AddRecipeOptionsDialog (spec 069)", () => {
  it("has no 'Recipe from another notebook' without the prop (personal notebooks)", () => {
    render();
    expect(labels()).toEqual(["URL", "Picture", "Text", "Write it myself"]);
  });

  it("lists it last, after URL, Picture, Text and Write it myself, and calls back on a tap", () => {
    const onChooseFromNotebook = vi.fn();
    render({ onChooseFromNotebook });
    expect(labels()).toEqual(["URL", "Picture", "Text", "Write it myself", "Recipe from another notebook"]);

    const option = Array.from(document.querySelectorAll("[role='list'] button")).at(-1) as HTMLButtonElement;
    act(() => option.click());

    expect(onChooseFromNotebook).toHaveBeenCalledTimes(1);
  });

  it("shows it disabled with its reason, and a tap does nothing", () => {
    const onChooseFromNotebook = vi.fn();
    render({ onChooseFromNotebook, fromNotebookDisabledReason: "Join or create a kitchen first." });

    const option = Array.from(document.querySelectorAll("[role='list'] button")).at(-1) as HTMLButtonElement;
    expect(option.getAttribute("aria-disabled")).toBe("true");
    expect(option.textContent).toContain("Join or create a kitchen first.");
    act(() => option.click());

    expect(onChooseFromNotebook).not.toHaveBeenCalled();
  });
});
