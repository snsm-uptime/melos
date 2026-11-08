import { describe, expect, it } from "vitest";

import type { CaptureState } from "./captureStore";
import { buildSaveBody } from "./saveClient";

const base = {
  notebook: { id: "nb-1", kind: "personal", name: "Ana's", kitchenId: null, returnPath: "/x" },
  saveKey: "key-1",
  text: "",
  language: "en",
} as unknown as CaptureState;

const draft = {
  title: "Soup",
  baseServings: 4,
  servingsEstimated: false,
  lines: [],
  steps: [{ key: "s", text: "Stir." }],
  catalog: [],
};

describe("buildSaveBody for a picture draft", () => {
  it("sends the photo source with empty text and no address", () => {
    const state = { ...base, draft: { ...draft, fromPicture: true } } as unknown as CaptureState;
    const body = buildSaveBody(state, "data:image/webp;base64,AAAA");
    expect(body).toMatchObject({ source_kind: "photo", source_text: "" });
    expect(body).not.toHaveProperty("source_url");
    expect(body).toMatchObject({ preview_image: "data:image/webp;base64,AAAA" });
  });

  it("sends no preview when the member removed it", () => {
    const state = { ...base, draft: { ...draft, fromPicture: true } } as unknown as CaptureState;
    expect(buildSaveBody(state, null)).not.toHaveProperty("preview_image");
  });

  it("a text draft sends no source kind and the trimmed text, as before", () => {
    const state = { ...base, text: "  2 onions  ", draft } as unknown as CaptureState;
    const body = buildSaveBody(state);
    expect(body).not.toHaveProperty("source_kind");
    expect(body).toMatchObject({ source_text: "2 onions" });
  });

  it("a link draft still sends its address", () => {
    const state = {
      ...base,
      draft: { ...draft, sourceUrl: "https://example.test/x" },
    } as unknown as CaptureState;
    const body = buildSaveBody(state);
    expect(body).toMatchObject({ source_url: "https://example.test/x", source_text: "" });
    expect(body).not.toHaveProperty("source_kind");
  });
});
