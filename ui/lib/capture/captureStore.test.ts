import { beforeEach, describe, expect, it } from "vitest";

import {
  backToSheet,
  clearCapture,
  discardDraft,
  editDraft,
  getCaptureState,
  isDraftEdited,
  openSheet,
  setText,
  showDraft,
  type CaptureNotebook,
  type DraftView,
} from "./captureStore";

const notebook: CaptureNotebook = {
  id: "nb-1",
  kind: "personal",
  name: "ana's Notebook",
  kitchenId: null,
  returnPath: "/notebooks",
};

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

beforeEach(() => clearCapture());

describe("capture store", () => {
  it("keeps the pasted text when Back returns to the sheet (FR-031)", () => {
    openSheet(notebook);
    setText("2 large onions");
    showDraft(draft, "en");

    backToSheet();

    expect(getCaptureState().text).toBe("2 large onions");
    expect(getCaptureState().draft).toBeNull();
    expect(getCaptureState().sheetOpen).toBe(true);
  });

  it("clears the text and the draft on Discard (FR-020)", () => {
    openSheet(notebook);
    setText("2 large onions");
    showDraft(draft, "en");

    discardDraft();

    expect(getCaptureState().text).toBe("");
    expect(getCaptureState().draft).toBeNull();
    expect(getCaptureState().sheetOpen).toBe(true);
  });

  it("empties everything when the store is cleared (reload or leave)", () => {
    openSheet(notebook);
    setText("text");
    clearCapture();
    expect(getCaptureState()).toMatchObject({ notebook: null, text: "", sheetOpen: false });
  });
});

describe("isDraftEdited (FR-032)", () => {
  it("is false for a draft as first shown", () => {
    showDraft(draft, "en");
    expect(isDraftEdited(getCaptureState())).toBe(false);
  });

  it("is true after a change, and false again when the change is reverted by hand", () => {
    showDraft(draft, "en");

    editDraft({ ...draft, title: "Onion stew" });
    expect(isDraftEdited(getCaptureState())).toBe(true);

    editDraft({ ...draft, title: "Onion soup" });
    expect(isDraftEdited(getCaptureState())).toBe(false);
  });
});
