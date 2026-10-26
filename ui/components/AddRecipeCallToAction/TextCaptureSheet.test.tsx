/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearCapture, getCaptureState, openSheet } from "@/lib/capture/captureStore";

import { TextCaptureSheet } from "./TextCaptureSheet";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));

const candidates = [
  { id: "nb-1", name: "ana's Notebook", kind: "personal" as const, kitchenId: null },
  { id: "nb-2", name: "Family list", kind: "personal" as const, kitchenId: null },
];

const okResponse = {
  outcome: "draft",
  notebook: { id: "nb-1", kind: "personal", name: "ana's Notebook", kitchen_id: null },
  language: "en",
  draft: {
    title: "Onion soup",
    base_servings: 4,
    servings_estimated: true,
    main_ingredients: [],
    cuisines: [{ id: "international", label: "International", tag: null }],
    ingredient_lines: [
      { name: "onion", vague: false, quantity: 2, unit: "unit", size: "large", preparation: "chopped", note: null },
    ],
    steps: ["Simmer."],
  },
};

let container: HTMLDivElement;
let root: Root;

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function render() {
  act(() => {
    root.render(<TextCaptureSheet open candidates={candidates} onDraftReady={() => push("/notebooks/draft")} />);
  });
}

function setValue(element: HTMLTextAreaElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
  act(() => {
    setter.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function submitButton(): HTMLButtonElement {
  return Array.from(document.querySelectorAll("button")).find(
    (el) => el.textContent === "Read recipe" || el.textContent === "Reading your recipe…",
  ) as HTMLButtonElement;
}

beforeEach(() => {
  clearCapture();
  push.mockReset();
  openSheet({ id: "nb-1", kind: "personal", name: "ana's Notebook", kitchenId: null, returnPath: "/notebooks" });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(200, { max_text_chars: 5000 })));
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

describe("TextCaptureSheet", () => {
  it("keeps submit disabled while the text is empty or only spaces", () => {
    render();
    expect(submitButton().disabled).toBe(true);
    setValue(document.querySelector("textarea")!, "   ");
    expect(submitButton().disabled).toBe(true);
  });

  it("disables submit and shows the length message when the text is over the limit", () => {
    render();
    setValue(document.querySelector("textarea")!, "x".repeat(5001));
    expect(submitButton().disabled).toBe(true);
    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "That text is too long. Paste up to 5000 characters.",
    );
  });

  it("shows the message for a failure and keeps the text", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(200, { max_text_chars: 5000 }))
        .mockResolvedValueOnce(json(422, { code: "not_a_recipe", detail: "not_food" })),
    );
    render();
    setValue(document.querySelector("textarea")!, "What's the weather tomorrow?");

    await act(async () => submitButton().click());

    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "That doesn't look like a recipe. It is not about food. Paste the full recipe, with its ingredients and steps.",
    );
    expect(document.querySelector("textarea")!.value).toBe("What's the weather tomorrow?");
    expect(getCaptureState().draft).toBeNull();
  });

  it("names the ingredient in a question about it and keeps the text", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(200, { max_text_chars: 5000 }))
        .mockResolvedValueOnce(
          json(422, { code: "not_a_recipe", detail: "question_or_request", ingredient: "butter" }),
        ),
    );
    render();
    setValue(document.querySelector("textarea")!, "What's the total grams of a bar of butter?");

    await act(async () => submitButton().click());

    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "That reads as a question about butter, not a recipe. Clarify the text: paste the full recipe, with the amount and unit of butter and its steps.",
    );
    expect(document.querySelector("textarea")!.value).toBe("What's the total grams of a bar of butter?");
  });

  it("shows the new wording when more than one recipe is pasted", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(200, { max_text_chars: 5000 }))
        .mockResolvedValueOnce(json(422, { code: "one_recipe_at_a_time", detail: "" })),
    );
    render();
    setValue(document.querySelector("textarea")!, "Soup\n...\nCake\n...");

    await act(async () => submitButton().click());

    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "Only one recipe can be added at a time. Paste them one by one.",
    );
  });

  it("asks for the missing title and keeps the pasted text", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(200, { max_text_chars: 5000 }))
        .mockResolvedValueOnce(json(422, { code: "draft_incomplete", detail: "", missing: ["title"] })),
    );
    render();
    setValue(document.querySelector("textarea")!, "2 large onions, chopped.");

    await act(async () => submitButton().click());

    expect(document.querySelector("[role='alert']")?.textContent).toBe("Add a title for the recipe.");
    expect(document.querySelector("textarea")!.value).toBe("2 large onions, chopped.");
  });

  it("says the app could not build a recipe and keeps the pasted text", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(200, { max_text_chars: 5000 }))
        .mockResolvedValueOnce(json(422, { code: "ai_invalid_output", detail: "" })),
    );
    render();
    setValue(document.querySelector("textarea")!, "2 large onions, chopped.");

    await act(async () => submitButton().click());

    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "The app could not build a recipe from this text. Try again, or shorten the text to one recipe.",
    );
    expect(document.querySelector("textarea")!.value).toBe("2 large onions, chopped.");
  });

  it("names the ingredient that needs a unit", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(200, { max_text_chars: 5000 }))
        .mockResolvedValueOnce(
          json(422, {
            code: "ingredient_line_problem",
            detail: "",
            line_problems: [{ name: "butter", kind: "unit_missing" }],
          }),
        ),
    );
    render();
    setValue(document.querySelector("textarea")!, "1/4 butter");

    await act(async () => submitButton().click());

    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "Add a unit to butter, such as grams, cups or units.",
    );
  });

  it("stores the draft and moves to the draft route on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(200, { max_text_chars: 5000 }))
        .mockResolvedValueOnce(json(200, okResponse)),
    );
    render();
    setValue(document.querySelector("textarea")!, "2 large onions, chopped.");

    await act(async () => submitButton().click());

    expect(getCaptureState().phase).toBe("draft");
    expect(getCaptureState().draft?.lines[0]).toMatchObject({ name: "onion", preparation: "chopped" });
    expect(push).toHaveBeenCalledWith("/notebooks/draft");
  });

  it("shows the notebook picker with the choices when there is more than one", () => {
    render();
    const options = Array.from(document.querySelectorAll("select option")).map((o) => o.textContent);
    expect(options).toEqual(["ana's Notebook", "Family list"]);
  });
});
