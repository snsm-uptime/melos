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
  catalog: ["onion"],
  draft: {
    title: "Onion soup",
    base_servings: 4,
    servings_estimated: true,
    // MVP-OUT: main_ingredients: [],
    // MVP-OUT: cuisines: [{ id: "international", label: "International", tag: null }],
    changes: [],
    ingredient_lines: [
      {
        name: "onion",
        vague: false,
        quantity: 2,
        unit: "unit",
        size: "large",
        preparation: "chopped",
        note: null,
        text_name: "onion",
        match: { kind: "matched", entry: "onion" },
      },
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

  describe("my own notebook (new), spec 035 research R6", () => {
    const kitchenCandidates = [
      { id: "own-new", name: "My own notebook (new)", kind: "kitchen" as const, kitchenId: "k1" },
      { id: "nb-ben", name: "ben's Notebook", kind: "kitchen" as const, kitchenId: "k1" },
    ];
    const made = { id: "nb-own", name: "ana's (Home) Notebook", kind: "kitchen", kitchen_id: "k1" };

    function renderKitchen() {
      openSheet({
        id: "own-new",
        kind: "kitchen",
        name: "My own notebook (new)",
        kitchenId: "k1",
        returnPath: "/kitchens/k1",
      });
      act(() => {
        root.render(
          <TextCaptureSheet open candidates={kitchenCandidates} onDraftReady={() => {}} />,
        );
      });
    }

    function stubRoutes(capture: () => Response, own: () => Response = () => json(200, made)) {
      const calls: string[] = [];
      vi.stubGlobal(
        "fetch",
        vi.fn(async (url: string) => {
          calls.push(url);
          if (url.endsWith("/capture-notebook")) return own();
          if (url.endsWith("/captures/text")) return capture();
          return json(200, { max_text_chars: 5000 });
        }),
      );
      return calls;
    }

    async function submit() {
      setValue(document.querySelector("textarea")!, "Onion soup");
      await act(async () => {
        submitButton().click();
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    }

    it("makes the notebook first and captures into it, never into own-new", async () => {
      const calls = stubRoutes(() => json(200, okResponse));
      renderKitchen();

      await submit();

      const made_at = calls.findIndex((url) => url.endsWith("/capture-notebook"));
      const captured_at = calls.findIndex((url) => url.endsWith("/captures/text"));
      expect(made_at).toBeGreaterThan(-1);
      expect(captured_at).toBeGreaterThan(made_at);
      expect(calls[captured_at]).toBe("/api/notebooks/nb-own/captures/text");
      expect(calls.join()).not.toContain("own-new/");
      expect(getCaptureState().notebook?.id).toBe("nb-own");
    });

    it("keeps the text and shows a message when the notebook can't be made", async () => {
      const calls = stubRoutes(
        () => json(200, okResponse),
        () => json(403, { code: "kitchen_archived" }),
      );
      renderKitchen();

      await submit();

      expect(calls.some((url) => url.endsWith("/captures/text"))).toBe(false);
      expect(getCaptureState().text).toBe("Onion soup");
      expect(document.querySelector("[role='alert']")).not.toBeNull();
    });

    it("shows the real notebook in the picker after a failed extraction", async () => {
      stubRoutes(() => json(422, { code: "ai_invalid_output" }));
      renderKitchen();

      await submit();

      const select = document.querySelector("select") as HTMLSelectElement;
      expect(select.value).toBe("nb-own");
      expect(select.options[0].textContent).toBe("ana's (Home) Notebook");
    });

    it("sends an explicit pick straight to it and makes no notebook", async () => {
      const calls = stubRoutes(() => json(200, okResponse));
      renderKitchen();
      const select = document.querySelector("select") as HTMLSelectElement;
      act(() => {
        select.value = "nb-ben";
        select.dispatchEvent(new Event("change", { bubbles: true }));
      });

      await submit();

      expect(calls.some((url) => url.endsWith("/capture-notebook"))).toBe(false);
      expect(calls).toContain("/api/notebooks/nb-ben/captures/text");
    });
  });
});
