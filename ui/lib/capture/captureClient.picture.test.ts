import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { submitPictureCapture } from "./captureClient";

// The shrink is tested on its own; here the bytes sent must be the file's own bytes.
vi.mock("./pictureDownscale", () => ({
  downscalePicture: async (file: Blob) => file,
  PictureDecodeError: class extends Error {},
}));

const draftBody = {
  outcome: "draft",
  notebook: { id: "nb-1", kind: "personal", name: "Ana's", kitchen_id: null },
  language: "en",
  catalog: [],
  draft: {
    title: "Soup",
    base_servings: 4,
    servings_estimated: false,
    changes: [],
    ingredient_lines: [],
    steps: ["Stir."],
  },
  picture: {
    tier: "tier_3",
    sharpness: null,
    original_dimensions: [240, 180],
    final_dimensions: [240, 180],
    size_kb: 1.2,
    steps_taken: [{ quality: 90, max_side: 2400 }],
    preview_image: "data:image/webp;base64,UklGRg==",
  },
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function fetchMock() {
  return fetch as unknown as ReturnType<typeof vi.fn>;
}

describe("submitPictureCapture", () => {
  it("posts the standard base64 of every byte value with no data-URI prefix", async () => {
    const bytes = new Uint8Array(3_000_000);
    for (let i = 0; i < bytes.length; i++) bytes[i] = i % 256;
    fetchMock().mockResolvedValue(new Response(JSON.stringify(draftBody), { status: 200 }));

    await submitPictureCapture("nb-1", new File([bytes], "page.jpg", { type: "image/jpeg" }), true);

    const [url, init] = fetchMock().mock.calls[0];
    expect(url).toBe("/api/notebooks/nb-1/captures/picture");
    const sent = JSON.parse(init.body as string) as { image_base64: string; handwritten: boolean };
    expect(sent.handwritten).toBe(true);
    expect(sent.image_base64.startsWith("data:")).toBe(false);
    const decoded = Buffer.from(sent.image_base64, "base64");
    expect(decoded.length).toBe(bytes.length);
    expect(decoded.equals(Buffer.from(bytes))).toBe(true);
  });

  it("sends handwritten false when the switch is off", async () => {
    fetchMock().mockResolvedValue(new Response(JSON.stringify(draftBody), { status: 200 }));
    await submitPictureCapture("nb-1", new File(["x"], "p.jpg"), false);
    const sent = JSON.parse(fetchMock().mock.calls[0][1].body as string) as { handwritten: boolean };
    expect(sent.handwritten).toBe(false);
  });

  it("returns the draft with the picture metadata", async () => {
    fetchMock().mockResolvedValue(new Response(JSON.stringify(draftBody), { status: 200 }));
    const result = await submitPictureCapture("nb-1", new File(["x"], "p.jpg"), true);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.picture?.tier).toBe("tier_3");
      expect(result.value.picture?.preview_image).toMatch(/^data:image\/webp;base64,/);
    }
  });

  it("returns the server's error code as the message", async () => {
    fetchMock().mockResolvedValue(
      new Response(JSON.stringify({ code: "not_a_recipe", detail: "not_food" }), { status: 422 }),
    );
    const result = await submitPictureCapture("nb-1", new File(["x"], "p.jpg"), true);
    expect(result).toEqual({
      ok: false,
      message: expect.objectContaining({ code: "not_a_recipe", reason: "not_food" }),
    });
  });

  it("answers ai_unavailable when the network fails", async () => {
    fetchMock().mockRejectedValue(new TypeError("network"));
    const result = await submitPictureCapture("nb-1", new File(["x"], "p.jpg"), true);
    expect(result).toEqual({ ok: false, message: { code: "ai_unavailable" } });
  });
});
