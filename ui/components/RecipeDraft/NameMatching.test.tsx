/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearCapture,
  getCaptureState,
  openSheet,
  setText,
  showDraft,
  type DraftView,
  type LineView,
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
  // MVP-OUT: main_ingredients: [],
  // MVP-OUT: cuisines: [],
};

const onion: LineView = {
  key: "l1",
  name: "onion",
  vague: false,
  quantity: 2,
  unit: "unit",
  size: "large",
  preparation: null,
  note: null,
  textName: "onions",
  match: { kind: "matched", entry: "onion" },
};

const flour: LineView = {
  key: "l2",
  name: "flour",
  vague: false,
  quantity: 200,
  unit: "g",
  size: null,
  preparation: null,
  note: null,
  textName: "flour",
  match: { kind: "new", entry: null },
};

const draft: DraftView = {
  title: "Onion soup",
  baseServings: 4,
  servingsEstimated: false,
  // MVP-OUT: mainIngredients: [],
  // MVP-OUT: cuisines: [],
  lines: [onion, flour],
  steps: [{ key: "s1", text: "Simmer." }],
  catalog: ["flour", "onion", "spring onion"],
};

let container: HTMLDivElement;
let root: Root;

function buttonByText(text: string): HTMLButtonElement {
  return Array.from(document.querySelectorAll("button")).find(
    (el) => el.textContent?.trim() === text,
  ) as HTMLButtonElement;
}

function matchSelects(): HTMLSelectElement[] {
  return Array.from(
    document.querySelectorAll<HTMLSelectElement>(
      "select[aria-label='Catalog match']",
    ),
  );
}

/** Set a controlled select's value the way a user does, so React sees the change. */
function chooseInSelect(select: HTMLSelectElement, value: string): void {
  const setter = Object.getOwnPropertyDescriptor(
    HTMLSelectElement.prototype,
    "value",
  )!.set!;
  setter.call(select, value);
  select.dispatchEvent(new Event("change", { bubbles: true }));
}

beforeEach(() => {
  clearCapture();
  push.mockReset();
  replace.mockReset();
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify(vocabulary), { status: 200 }),
      ),
  );
  openSheet({
    id: "nb-1",
    kind: "personal",
    name: "ana's Notebook",
    kitchenId: null,
    returnPath: "/notebooks",
  });
  setText("2 large onions\n200 g flour");
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

describe("ingredient match labels (spec 018 US1)", () => {
  it("selects the matched entry for the matching line and new ingredient for the other", async () => {
    await act(async () => {
      root.render(<RecipeDraftEditor />);
    });

    const [first, second] = matchSelects();
    expect(first.value).toBe("onion");
    expect(second.selectedOptions[0].textContent).toBe("new ingredient");
  });
});

describe("name changes (spec 018 US2)", () => {
  it("shows the change as a row above the affected line's card and nowhere else", async () => {
    await act(async () => {
      root.render(<RecipeDraftEditor />);
    });

    const items = Array.from(container.querySelectorAll("li")).filter((li) =>
      li.querySelector("[aria-label='Catalog match'], select"),
    );
    const [first, second] = items;
    const notice = first.querySelector("[data-name-change]");
    expect(notice?.textContent).toContain("onions → onion");
    // The row comes before the card inside the same list item.
    expect(first.firstElementChild).toBe(notice);
    expect(second.querySelector("[data-name-change]")).toBeNull();
    expect(container.querySelectorAll("[data-name-change]")).toHaveLength(1);
    expect(container.textContent).not.toContain("Names changed");
  });

  it("shows the change and undo returns only that line to its text name", async () => {
    await act(async () => {
      root.render(<RecipeDraftEditor />);
    });

    expect(container.textContent).toContain("onions → onion");

    act(() => buttonByText("Undo").click());

    expect(container.textContent).not.toContain("onions → onion");
    const [first, second] = getCaptureState().draft!.lines;
    expect(first).toMatchObject({
      name: "onions",
      match: { kind: "new", entry: null },
    });
    expect(second.name).toBe("flour");
  });
});

describe("match control (spec 018 US3)", () => {
  it("choosing another catalog entry updates the selection and the change list", async () => {
    await act(async () => {
      root.render(<RecipeDraftEditor />);
    });

    act(() => chooseInSelect(matchSelects()[0], "spring onion"));

    expect(matchSelects()[0].value).toBe("spring onion");
    expect(container.textContent).toContain("onions → spring onion");
  });

  it("choosing new ingredient clears the match and the change", async () => {
    await act(async () => {
      root.render(<RecipeDraftEditor />);
    });

    act(() => chooseInSelect(matchSelects()[0], "__new__"));

    expect(matchSelects()[0].value).toBe("__new__");
    expect(container.textContent).not.toContain("onions → onion");
  });
});
