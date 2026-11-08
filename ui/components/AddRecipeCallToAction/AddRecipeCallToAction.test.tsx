/** @vitest-environment jsdom */

import { notebookPicker, pickedNotebook } from "@/components/NotebookPicker/testHelpers";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearCapture } from "@/lib/capture/captureStore";

import { AddRecipeCallToAction, type CaptureCandidate } from "./AddRecipeCallToAction";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
  usePathname: () => "/notebooks",
}));

const candidates: CaptureCandidate[] = [
  { id: "nb-default", name: "ana's Notebook", kind: "personal", kitchenId: null },
  { id: "nb-family", name: "Family list", kind: "personal", kitchenId: null },
];

let container: HTMLDivElement;
let root: Root;

function render(list = candidates, variant?: "placeholder" | "button") {
  act(() => {
    root.render(
      <AddRecipeCallToAction
        candidates={list}
        defaultId="nb-default"
        returnPath="/notebooks"
        variant={variant}
      />,
    );
  });
}

function button(label: string): HTMLButtonElement | null {
  const found = Array.from(document.querySelectorAll("button")).find(
    (el) => el.getAttribute("aria-label") === label || el.textContent?.trim() === label,
  );
  return found ?? null;
}

beforeEach(() => {
  clearCapture();
  push.mockReset();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify({ max_text_chars: 5000 }), { status: 200 })),
  );
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

describe("AddRecipeCallToAction", () => {
  it("shows the placeholder with the accessible name 'Add a recipe'", () => {
    render();
    expect(button("Add a recipe")).not.toBeNull();
  });

  it("as a button it reads 'Add recipe' and opens the same options dialog", () => {
    render(candidates, "button");
    expect(button("Add a recipe")).toBeNull();

    act(() => button("Add recipe")!.click());

    expect(button("Text")).not.toBeNull();
  });

  it("opens the options dialog with URL, Picture, Text, Write it myself and Recipe from another notebook in order, and no confirm or cancel", () => {
    render();

    act(() => button("Add a recipe")!.click());

    const items = Array.from(document.querySelectorAll("[role='list'] button")).map((el) => ({
      text: el.textContent?.trim(),
      disabled: el.getAttribute("aria-disabled"),
    }));
    expect(items).toEqual([
      { text: "URL", disabled: null },
      { text: "Picture", disabled: null },
      { text: "Text", disabled: null },
      { text: "Write it myselfAn empty recipe, no assistant", disabled: null },
      { text: "Copy recipe from notebook", disabled: null },
    ]);
    expect(button("Cancel")).toBeNull();
    expect(button("Confirm")).toBeNull();
  });

  it("opens the text sheet for the preselected notebook when Text is chosen", () => {
    render();
    act(() => button("Add a recipe")!.click());

    act(() => button("Text")!.click());

    expect(document.querySelector("[role='dialog']")?.textContent).toContain("ana's Notebook");
    expect(document.querySelector("textarea")).not.toBeNull();
  });

  it("opens the link sheet for the preselected notebook when URL is chosen (spec 026)", () => {
    render();
    act(() => button("Add a recipe")!.click());

    act(() => button("URL")!.click());

    const dialog = document.querySelector("[role='dialog']");
    expect(dialog?.textContent).toContain("ana's Notebook");
    expect(dialog?.querySelector("input[type='url']")).not.toBeNull();
    expect(document.querySelector("textarea")).toBeNull();
  });

  it("Picture opens the picture sheet with a file input and no text or link field", () => {
    render();
    act(() => button("Add a recipe")!.click());

    act(() => button("Picture")!.click());

    expect(document.querySelector("input[type='file']")).not.toBeNull();
    expect(document.querySelector("input[type='url']")).toBeNull();
    expect(document.querySelector("textarea")).toBeNull();
  });

  it("shows the notebook picker only when there is more than one notebook", () => {
    render([candidates[0]]);
    act(() => button("Add a recipe")!.click());
    act(() => button("Text")!.click());
    expect(notebookPicker()).toBeNull();
  });

  it("shows the picker for the new-notebook row and one other notebook", () => {
    const list: CaptureCandidate[] = [
      { id: "own-new", name: "My own notebook (new)", kind: "kitchen", kitchenId: "k1" },
      { id: "nb-kitchen", name: "ben's (Home) Notebook", kind: "kitchen", kitchenId: "k1" },
    ];
    act(() => {
      root.render(
        <AddRecipeCallToAction candidates={list} defaultId="own-new" returnPath="/kitchens/k1" />,
      );
    });
    act(() => button("Add a recipe")!.click());
    act(() => button("Text")!.click());

    expect(pickedNotebook()).toBe("My own notebook (new)");
  });
});
