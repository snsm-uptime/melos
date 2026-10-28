import { afterEach, describe, expect, it, vi } from "vitest";

import type { CaptureState } from "./captureStore";
import { buildSaveBody, submitSave } from "./saveClient";

function state(overrides: Partial<CaptureState> = {}): CaptureState {
  return {
    notebook: {
      id: "nb-1",
      kind: "personal",
      name: "ana's Notebook",
      kitchenId: null,
      returnPath: "/notebooks",
    },
    text: "  2 large onions.  ",
    sheetOpen: false,
    phase: "draft",
    message: null,
    draft: {
      title: "Onion soup",
      baseServings: 4,
      servingsEstimated: false,
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
          textName: "onions",
          match: { kind: "matched", entry: "onion" },
        },
        {
          key: "l2",
          name: "salt",
          vague: true,
          quantity: null,
          unit: null,
          size: null,
          preparation: null,
          note: "a pinch",
          textName: "salt",
          match: { kind: "new", entry: null },
        },
      ],
      steps: [{ key: "s1", text: "Simmer." }],
      catalog: ["onion"],
    },
    originalHash: "x",
    language: "en",
    saveKey: "key-1",
    saving: false,
    savedNotice: null,
    ...overrides,
  };
}

afterEach(() => vi.unstubAllGlobals());

function stubFetch(response: Response | Error) {
  const fetchMock = vi.fn(async () => {
    if (response instanceof Error) throw response;
    return response;
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("buildSaveBody", () => {
  it("sends the edited values, the trimmed text and the key, and no match flags", () => {
    expect(buildSaveBody(state())).toEqual({
      save_key: "key-1",
      notebook_id: "nb-1",
      source_text: "2 large onions.",
      title: "Onion soup",
      base_servings: 4,
      servings_estimated: false,
      ingredient_lines: [
        {
          name: "onion",
          vague: false,
          quantity: 2,
          unit: "unit",
          size: "large",
          preparation: "chopped",
          note: null,
        },
        {
          name: "salt",
          vague: true,
          quantity: null,
          unit: null,
          size: null,
          preparation: null,
          note: "a pinch",
        },
      ],
      steps: ["Simmer."],
    });
  });

  it("returns null when there is no draft, notebook or key", () => {
    expect(buildSaveBody(state({ draft: null }))).toBeNull();
    expect(buildSaveBody(state({ notebook: null }))).toBeNull();
    expect(buildSaveBody(state({ saveKey: null }))).toBeNull();
  });
});

describe("submitSave", () => {
  it.each([200, 201])("is ok on %s", async (status) => {
    const fetchMock = stubFetch(new Response("{}", { status }));
    expect(await submitSave(state())).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/recipes",
      expect.objectContaining({ method: "POST", credentials: "same-origin" }),
    );
  });

  it("maps a missing notebook to its own code", async () => {
    stubFetch(new Response(JSON.stringify({ code: "notebook_not_found" }), { status: 404 }));
    expect(await submitSave(state())).toEqual({
      ok: false,
      message: { code: "notebook_gone", missing: undefined, lineProblems: undefined },
    });
  });

  it("passes the missing parts and line problems of an incomplete draft", async () => {
    stubFetch(
      new Response(
        JSON.stringify({
          code: "draft_incomplete",
          missing: ["title"],
          line_problems: [{ name: "flour", kind: "unit_missing" }, { kind: 3 }],
        }),
        { status: 422 },
      ),
    );
    expect(await submitSave(state())).toEqual({
      ok: false,
      message: {
        code: "draft_incomplete",
        missing: ["title"],
        lineProblems: [{ name: "flour", kind: "unit_missing" }],
      },
    });
  });

  it("answers a network failure and a non-JSON error as save_unavailable", async () => {
    stubFetch(new TypeError("offline"));
    expect(await submitSave(state())).toMatchObject({ ok: false, message: { code: "save_unavailable" } });
    stubFetch(new Response("<html>", { status: 502 }));
    expect(await submitSave(state())).toMatchObject({ ok: false, message: { code: "save_unavailable" } });
  });

  it("does not call the api when there is nothing to save", async () => {
    const fetchMock = stubFetch(new Response("{}", { status: 201 }));
    expect(await submitSave(state({ draft: null }))).toMatchObject({ ok: false });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
