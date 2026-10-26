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

  it("keeps the code, and the reason for not_a_recipe", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(respond(422, { code: "not_a_recipe", detail: "A weather question." })),
    );

    const result = await submitCapture("nb-1", "weather");

    expect(result).toEqual({
      ok: false,
      message: { code: "not_a_recipe", reason: "A weather question." },
      max: undefined,
    });
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
