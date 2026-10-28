import { describe, expect, it } from "vitest";

import { clearCapture, editDraft, isDraftEdited, showDraft, getCaptureState, openSheet, type DraftView } from "./captureStore";

const draft: DraftView = {
  title: "Onion soup",
  baseServings: 4,
  servingsEstimated: false,
  // MVP-OUT: mainIngredients: [],
  // MVP-OUT: cuisines: [],
  lines: [],
  steps: [{ key: "s1", text: "Simmer." }],
  catalog: [],
};

describe("leave guard state (FR-032)", () => {
  it("is off when nothing is open, so a plain leave is never blocked", () => {
    clearCapture();
    expect(isDraftEdited(getCaptureState())).toBe(false);
  });

  it("turns on once the draft is edited and off again after Discard", () => {
    clearCapture();
    openSheet({ id: "nb-1", kind: "personal", name: "ana's Notebook", kitchenId: null, returnPath: "/notebooks" });
    showDraft(draft, "en");
    editDraft({ ...draft, title: "Changed" });
    expect(isDraftEdited(getCaptureState())).toBe(true);
    clearCapture();
    expect(isDraftEdited(getCaptureState())).toBe(false);
  });
});
