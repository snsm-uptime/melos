import { afterEach, describe, expect, it, vi } from "vitest";

import { submitCapture } from "./captureClient";

const okBody = {
  outcome: "draft",
  notebook: { id: "nb-1", kind: "personal", name: "ana's Notebook", kitchen_id: null },
  language: "es",
  draft: {
    title: "Onion soup",
    base_servings: 4,
    servings_estimated: true,
    main_ingredients: [],
    cuisines: [{ id: "international", label: "Internacional", tag: null }],
    ingredient_lines: [],
    steps: ["Simmer."],
  },
};

function respond(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

afterEach(() => vi.restoreAllMocks());

describe("submitCapture", () => {
  it("posts the text to the notebook's capture route and returns the draft", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond(200, okBody));
    vi.stubGlobal("fetch", fetchMock);

    const result = await submitCapture("nb-1", "2 onions");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/notebooks/nb-1/captures/text",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ text: "2 onions" }) }),
    );
    expect(result.ok).toBe(true);
  });

  it("keeps the code, the reason enum and the ingredient for not_a_recipe", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          respond(422, { code: "not_a_recipe", detail: "story_or_article", ingredient: "butter" }),
        ),
    );

    const result = await submitCapture("nb-1", "Once upon a time");

    expect(result).toEqual({
      ok: false,
      message: { code: "not_a_recipe", reason: "story_or_article", ingredient: "butter" },
      max: undefined,
    });
  });

  it("keeps a null ingredient as null for not_a_recipe", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(respond(422, { code: "not_a_recipe", detail: "question_or_request", ingredient: null })),
    );

    const result = await submitCapture("nb-1", "What is the weather?");

    expect(result).toMatchObject({
      ok: false,
      message: { code: "not_a_recipe", reason: "question_or_request", ingredient: null },
    });
  });

  it("drops a free-text detail for not_a_recipe instead of showing it as a reason", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(respond(422, { code: "not_a_recipe", detail: "A weather question." })),
    );

    const result = await submitCapture("nb-1", "weather");

    expect(result).toMatchObject({ ok: false, message: { code: "not_a_recipe" } });
    if (result.ok) throw new Error("expected a refusal");
    expect(result.message.reason).toBeUndefined();
  });

  it("reads the limit from a text_too_long answer", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          respond(422, { code: "text_too_long", detail: "That text is too long. Paste up to 5000 characters." }),
        ),
    );

    const result = await submitCapture("nb-1", "x");

    expect(result).toMatchObject({ ok: false, max: 5000, message: { code: "text_too_long" } });
  });

  it("keeps the missing parts of a draft_incomplete answer and no reason", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(respond(422, { code: "draft_incomplete", detail: "", missing: ["title"] })),
    );

    const result = await submitCapture("nb-1", "2 onions");

    expect(result).toMatchObject({ ok: false, message: { code: "draft_incomplete", missing: ["title"] } });
    if (result.ok) throw new Error("expected a refusal");
    expect(result.message.reason).toBeUndefined();
  });

  it("maps each line problem with its name and kind", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        respond(422, {
          code: "ingredient_line_problem",
          detail: "",
          line_problems: [
            { name: "butter", kind: "unit_missing" },
            { name: "flour", kind: "unit_not_recognized" },
          ],
        }),
      ),
    );

    const result = await submitCapture("nb-1", "1/4 butter");

    expect(result).toMatchObject({
      ok: false,
      message: {
        code: "ingredient_line_problem",
        lineProblems: [
          { name: "butter", kind: "unit_missing" },
          { name: "flour", kind: "unit_not_recognized" },
        ],
      },
    });
  });

  it("keeps a null line problem name as null", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        respond(422, {
          code: "ingredient_line_problem",
          detail: "",
          line_problems: [{ name: null, kind: "quantity_missing" }],
        }),
      ),
    );

    const result = await submitCapture("nb-1", "butter");

    expect(result).toMatchObject({
      ok: false,
      message: { lineProblems: [{ name: null, kind: "quantity_missing" }] },
    });
  });

  it("maps a network failure and a 502 to ai_unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    expect(await submitCapture("nb-1", "x")).toMatchObject({
      ok: false,
      message: { code: "ai_unavailable" },
    });

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respond(502, { code: "bad_gateway" })));
    expect(await submitCapture("nb-1", "x")).toMatchObject({
      ok: false,
      message: { code: "ai_unavailable" },
    });
  });

  it("keeps the 429 code; the Retry-After header is read by the route, not here", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(respond(429, { code: "ai_limit_reached" }, { "Retry-After": "30" })),
    );

    expect(await submitCapture("nb-1", "x")).toMatchObject({
      ok: false,
      message: { code: "ai_limit_reached" },
    });
  });
});
