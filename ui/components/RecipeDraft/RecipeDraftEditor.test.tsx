/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearCapture,
  editDraft,
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

function update_title(title: string) {
  editDraft({ ...getCaptureState().draft!, title });
}

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
  it("shows the notebook line, the title and the ingredient row", async () => {
    await act(async () => {
      root.render(<RecipeDraftEditor />);
    });

    expect(container.textContent).toContain("ana's Notebook");
    expect((container.querySelector("h1 textarea") as HTMLTextAreaElement).value).toBe(
      "Onion soup",
    );
    expect(container.textContent).not.toContain("estimated");
    // MVP-OUT: expect(container.textContent).toContain("Aves");
    // MVP-OUT: expect(container.textContent).toContain("Internacional");
    expect(container.textContent).not.toContain("Main ingredients");
    expect(container.textContent).not.toContain("Cuisines");
    expect(container.querySelector("input[type='number']")).not.toBeNull();
  });

  describe("Save (spec 020)", () => {
    function stubFetch(save: () => Promise<Response> | Response) {
      const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
        void init;
        if (url === "/api/recipes") return save();
        return new Response(JSON.stringify(vocabulary), { status: 200 });
      });
      vi.stubGlobal("fetch", fetchMock);
      return fetchMock;
    }

    function saveCalls(fetchMock: ReturnType<typeof stubFetch>) {
      return fetchMock.mock.calls.filter(([url]) => url === "/api/recipes");
    }

    async function render() {
      await act(async () => {
        root.render(<RecipeDraftEditor />);
      });
    }

    async function pressSave() {
      await act(async () => {
        buttonByText("Save recipe").click();
      });
    }

    it("sends the edited draft, then clears it and returns to the notebook", async () => {
      const fetchMock = stubFetch(() => new Response("{}", { status: 201 }));
      await render();

      await pressSave();

      const [, init] = saveCalls(fetchMock)[0] as [string, RequestInit];
      const body = JSON.parse(init.body as string);
      expect(body).toMatchObject({
        notebook_id: "nb-1",
        title: "Onion soup",
        base_servings: 4,
        servings_estimated: true,
        source_text: "2 large onions, chopped.",
        steps: ["Simmer."],
      });
      expect(body.save_key).toEqual(expect.any(String));
      expect(getCaptureState()).toMatchObject({
        draft: null,
        text: "",
        saveKey: null,
        savedNotice: { returnPath: "/notebooks/nb-1" },
      });
      expect(push).toHaveBeenCalledWith("/notebooks/nb-1");
    });

    it("is disabled while the draft has a problem", async () => {
      stubFetch(() => new Response("{}", { status: 201 }));
      await render();
      expect(buttonByText("Save recipe").disabled).toBe(false);
      await act(async () => {
        editDraft({ ...getCaptureState().draft!, title: "" });
      });
      expect(buttonByText("Save recipe").disabled).toBe(true);
    });

    it("shows the busy state and ignores a second press while saving", async () => {
      let finish: (value: Response) => void = () => {};
      const fetchMock = stubFetch(() => new Promise<Response>((resolve) => (finish = resolve)));
      await render();

      await pressSave();
      expect(buttonByText("Saving…").disabled).toBe(true);
      await act(async () => {
        buttonByText("Saving…").click();
      });
      expect(saveCalls(fetchMock)).toHaveLength(1);

      await act(async () => finish(new Response("{}", { status: 201 })));
      expect(getCaptureState().draft).toBeNull();
    });

    it.each([
      [409, "kitchen_archived", "This kitchen is archived, so recipes can't be added."],
      [
        404,
        "notebook_not_found",
        "This notebook no longer exists, or you no longer have access to it.",
      ],
      [
        422,
        "invalid_recipe",
        "The recipe breaks a rule. Check the ingredient lines and try again.",
      ],
    ])("keeps the draft and shows a message on %s %s", async (status, code, message) => {
      stubFetch(() => new Response(JSON.stringify({ code, detail: "" }), { status }));
      await render();
      act(() => update_title("Better soup"));

      await pressSave();

      expect(container.textContent).toContain(message);
      expect(getCaptureState()).toMatchObject({ saving: false, text: "2 large onions, chopped." });
      expect(getCaptureState().draft?.title).toBe("Better soup");
      expect(buttonByText("Save recipe").disabled).toBe(false);
      expect(push).not.toHaveBeenCalled();
    });

    it("names the missing parts when the api reports them", async () => {
      stubFetch(
        () =>
          new Response(
            JSON.stringify({ code: "draft_incomplete", missing: ["steps"], line_problems: [] }),
            { status: 422 },
          ),
      );
      await render();
      await pressSave();
      expect(container.textContent).toContain("Add the steps of the recipe.");
    });

    it("keeps the draft after a network failure and retries with the same key", async () => {
      let attempt = 0;
      const fetchMock = stubFetch(() => {
        attempt += 1;
        if (attempt === 1) throw new TypeError("offline");
        return new Response("{}", { status: 200 });
      });
      await render();

      await pressSave();
      expect(container.textContent).toContain("We couldn't save the recipe.");
      expect(getCaptureState().draft).not.toBeNull();

      await pressSave();
      const keys = saveCalls(fetchMock).map(
        ([, init]) => JSON.parse((init as RequestInit).body as string).save_key,
      );
      expect(keys).toHaveLength(2);
      expect(keys[0]).toBe(keys[1]);
      expect(getCaptureState().draft).toBeNull();
    });
  });

  it("Discard clears the draft and the text, and returns to the notebook", async () => {
    await act(async () => {
      root.render(<RecipeDraftEditor />);
    });

    act(() => buttonByText("Discard").click());

    expect(getCaptureState()).toMatchObject({
      draft: null,
      text: "",
      sheetOpen: true,
    });
    expect(push).toHaveBeenCalledWith("/notebooks");
  });

  it("Back keeps the pasted text and drops the draft", async () => {
    await act(async () => {
      root.render(<RecipeDraftEditor />);
    });

    act(() =>
      (
        document.querySelector("button[aria-label='Back']") as HTMLButtonElement
      ).click(),
    );

    expect(getCaptureState()).toMatchObject({
      draft: null,
      text: "2 large onions, chopped.",
      sheetOpen: true,
    });
    expect(push).toHaveBeenCalledWith("/notebooks");
  });
});
