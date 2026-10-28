import { beforeEach, describe, expect, it } from "vitest";

import {
  backToSheet,
  clearCapture,
  discardDraft,
  editDraft,
  getCaptureState,
  failSave,
  isDraftEdited,
  markSaved,
  savedReturnPath,
  openSheet,
  setText,
  showDraft,
  startSave,
  takeSavedNotice,
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

  describe("Save (spec 020)", () => {
    it("makes a new save key for each draft shown and clears it on Back and Discard", () => {
      openSheet(notebook);
      showDraft(draft, "en");
      const first = getCaptureState().saveKey;
      expect(first).toEqual(expect.any(String));

      backToSheet();
      expect(getCaptureState().saveKey).toBeNull();

      showDraft(draft, "en");
      expect(getCaptureState().saveKey).not.toBe(first);
      discardDraft();
      expect(getCaptureState().saveKey).toBeNull();
    });

    it("keeps the draft, the text and the key when a save fails", () => {
      openSheet(notebook);
      setText("2 onions");
      showDraft(draft, "en");
      const key = getCaptureState().saveKey;

      startSave();
      expect(getCaptureState().saving).toBe(true);
      failSave({ code: "kitchen_archived" });

      expect(getCaptureState()).toMatchObject({
        saving: false,
        text: "2 onions",
        saveKey: key,
        message: { code: "kitchen_archived" },
      });
      expect(getCaptureState().draft).not.toBeNull();
    });

    it("clears the draft on success and gives the notice to its page once", () => {
      openSheet(notebook);
      setText("2 onions");
      showDraft(draft, "en");

      markSaved("/notebooks");

      expect(getCaptureState()).toMatchObject({ draft: null, text: "", saveKey: null });
      expect(takeSavedNotice("/kitchens/k1")).toBe(false);
      expect(takeSavedNotice("/notebooks")).toBe(true);
      expect(takeSavedNotice("/notebooks")).toBe(false);
    });
  });
});

describe("savedReturnPath", () => {
  it("returns a personal capture to its notebook page and a kitchen capture to its own path", () => {
    expect(
      savedReturnPath({
        id: "nb-1",
        kind: "personal",
        name: "ana's Notebook",
        kitchenId: null,
        returnPath: "/notebooks",
      }),
    ).toBe("/notebooks/nb-1");
    expect(
      savedReturnPath({
        id: "nb-2",
        kind: "kitchen",
        name: "Home",
        kitchenId: "k1",
        returnPath: "/kitchens/k1",
      }),
    ).toBe("/kitchens/k1");
  });
});
