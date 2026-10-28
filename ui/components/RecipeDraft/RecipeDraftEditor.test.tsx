/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearCapture,
  getCaptureState,
  openSheet,
  showDraft,
  setText,
  type DraftView,
} from "@/lib/capture/captureStore";

import { RecipeDraftEditor } from "./RecipeDraftEditor";

const push = vi.fn();
const replace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace }) }));

const vocabulary = {
  units: ["g", "kg", "oz", "lb", "ml", "l", "cup", "tbsp", "tsp", "unit"],
  sizes: ["small", "medium", "large"],
  // MVP-OUT: max_main_ingredients: 2,
  // MVP-OUT: max_cuisines: 2,
  max_text_chars: 5000,
  // MVP-OUT: main_ingredients: [{ id: "poultry", label: { en: "Poultry", es: "Aves" } }],
  // MVP-OUT: cuisines: [{ id: "international", label: { en: "International", es: "Internacional" }, tag: null }],
};

const draft: DraftView = {
  title: "Onion soup",
  baseServings: 4,
  servingsEstimated: true,
  // MVP-OUT: mainIngredients: [{ id: "poultry", label: "Aves", tag: null }],
  // MVP-OUT: cuisines: [{ id: "international", label: "Internacional", tag: null }],
  lines: [
    {
      key: "l1",
      name: "onion",
      vague: false,
      quantity: 2,
      unit: "unit",
      size: "large",
      preparation: "chopped",
      note: null,
      textName: "onion",
      match: { kind: "new", entry: null },
    },
  ],
  steps: [{ key: "s1", text: "Simmer." }],
  catalog: ["onion", "spring onion"],
};

let container: HTMLDivElement;
let root: Root;

function buttonByText(text: string): HTMLButtonElement {
  return Array.from(document.querySelectorAll("button")).find(
    (el) => el.textContent?.trim() === text,
  ) as HTMLButtonElement;
}

beforeEach(() => {
  clearCapture();
  push.mockReset();
  replace.mockReset();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(vocabulary), { status: 200 })),
  );
  openSheet({ id: "nb-1", kind: "personal", name: "ana's Notebook", kitchenId: null, returnPath: "/notebooks" });
  setText("2 large onions, chopped.");
  showDraft(draft, "en");
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

describe("RecipeDraftEditor", () => {
  it("shows the notebook line, the title, the estimated badge and the ingredient row", async () => {
    await act(async () => {
      root.render(<RecipeDraftEditor />);
    });

    expect(container.textContent).toContain("For: ana's Notebook");
    expect((container.querySelector("input") as HTMLInputElement).value).toBe("Onion soup");
    expect(container.textContent).toContain("estimated");
    // MVP-OUT: expect(container.textContent).toContain("Aves");
    // MVP-OUT: expect(container.textContent).toContain("Internacional");
    expect(container.textContent).not.toContain("Main ingredients");
    expect(container.textContent).not.toContain("Cuisines");
    expect(container.querySelector("input[type='number']")).not.toBeNull();
  });

  it("has no Save control (FR-019)", async () => {
    await act(async () => {
      root.render(<RecipeDraftEditor />);
    });
    expect(buttonByText("Save")).toBeUndefined();
  });

  it("Discard clears the draft and the text, and returns to the notebook", async () => {
    await act(async () => {
      root.render(<RecipeDraftEditor />);
    });

    act(() => buttonByText("Discard").click());

    expect(getCaptureState()).toMatchObject({ draft: null, text: "", sheetOpen: true });
    expect(push).toHaveBeenCalledWith("/notebooks");
  });

  it("Back keeps the pasted text and drops the draft", async () => {
    await act(async () => {
      root.render(<RecipeDraftEditor />);
    });

    act(() => buttonByText("Back").click());

    expect(getCaptureState()).toMatchObject({ draft: null, text: "2 large onions, chopped.", sheetOpen: true });
    expect(push).toHaveBeenCalledWith("/notebooks");
  });
});
