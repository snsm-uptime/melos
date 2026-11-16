/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
  closeSheet,
  openSheet,
  removePreviewImage,
  setLink,
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

  it("opens for the page asking, even when the notebook is the one used last", () => {
    const notebook = { id: "nb-1", kind: "personal" as const, name: "Mine", kitchenId: null };
    openSheet({ ...notebook, returnPath: "/notebooks" });
    closeSheet();

    openSheet({ ...notebook, returnPath: "/notebooks/nb-1" });

    expect(getCaptureState().notebook?.returnPath).toBe("/notebooks/nb-1");
  });
});

describe("link capture (spec 026)", () => {
  const LINK = "https://example.test/soup";
  const linkDraft: DraftView = {
    ...draft,
    sourceUrl: LINK,
    previewImage: "data:image/jpeg;base64,AAAA",
    pageCut: false,
  };

  it("opens the text sheet by default and the link sheet when asked", () => {
    openSheet(notebook);
    expect(getCaptureState().source).toEqual({ kind: "text" });

    openSheet(notebook, "url");
    expect(getCaptureState().source).toEqual({ kind: "url", link: "" });
  });

  it("keeps a typed link when the notebook picker reopens the sheet", () => {
    openSheet(notebook, "url");
    setLink(LINK);

    openSheet({ ...notebook, id: "nb-2" });

    expect(getCaptureState().source).toEqual({ kind: "url", link: LINK });
  });

  it("keeps the link unchanged on Back (FR-018)", () => {
    openSheet(notebook, "url");
    setLink(LINK);
    showDraft(linkDraft, "en");

    backToSheet();

    expect(getCaptureState().source).toEqual({ kind: "url", link: LINK });
    expect(getCaptureState().sheetOpen).toBe(true);
  });

  it("clears the link on Discard and stays on the link sheet", () => {
    openSheet(notebook, "url");
    setLink(LINK);
    showDraft(linkDraft, "en");

    discardDraft();

    expect(getCaptureState().source).toEqual({ kind: "url", link: "" });
    expect(getCaptureState().draft).toBeNull();
  });

  it("clears the link after a successful Save", () => {
    openSheet(notebook, "url");
    setLink(LINK);
    showDraft(linkDraft, "en");

    markSaved("/notebooks");

    expect(getCaptureState().source).toEqual({ kind: "text" });
  });

  it("removing the photo empties it and counts as an edit", () => {
    showDraft(linkDraft, "en");

    removePreviewImage();

    expect(getCaptureState().draft?.previewImage).toBeNull();
    expect(getCaptureState().draft?.sourceUrl).toBe(LINK);
    expect(isDraftEdited(getCaptureState())).toBe(true);
  });

  it("a typed link clears an earlier message", () => {
    openSheet(notebook, "url");
    setLink("bad");
    failSave({ code: "page_fetch_failed" });

    setLink(LINK);

    expect(getCaptureState().message).toBeNull();
  });
});

describe("kept text (spec 076)", () => {
  const KEY = "melos.capture.text";
  type Store = typeof import("./captureStore");

  async function freshStore(): Promise<Store> {
    vi.resetModules();
    return import("./captureStore");
  }

  beforeEach(() => window.sessionStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("keeps the text in the tab's session storage, and removes the key when it is cleared", async () => {
    const store = await freshStore();
    store.setText("abc");
    expect(window.sessionStorage.getItem(KEY)).toBe("abc");
    store.setText("");
    expect(window.sessionStorage.getItem(KEY)).toBeNull();
  });

  it("starts from the kept text after a reload", async () => {
    window.sessionStorage.setItem(KEY, "2 large onions");
    const store = await freshStore();
    expect(store.getCaptureState().text).toBe("2 large onions");
  });

  it("does not drop the kept text when the store changes before it is first read", async () => {
    window.sessionStorage.setItem(KEY, "2 large onions");
    const store = await freshStore();
    store.openSheet(notebook, "text");
    expect(store.getCaptureState().text).toBe("2 large onions");
    expect(window.sessionStorage.getItem(KEY)).toBe("2 large onions");
  });

  it("keeps the text on close, Back, a refusal and the draft", async () => {
    const store = await freshStore();
    store.openSheet(notebook, "text");
    store.setText("abc");
    store.closeSheet();
    store.failSubmit({ code: "x" });
    store.showDraft(draft, "en");
    store.backToSheet();
    expect(window.sessionStorage.getItem(KEY)).toBe("abc");
    expect(store.getCaptureState().text).toBe("abc");
  });

  it.each([
    ["Save", (store: Store) => store.markSaved("/x")],
    ["Discard", (store: Store) => store.discardDraft()],
    ["a hand-written draft", (store: Store) => store.startManualDraft(notebook, "en")],
    ["clearKeptCaptureText", (store: Store) => store.clearKeptCaptureText()],
    ["leaving the draft", (store: Store) => store.clearCapture()],
  ])("removes the text on %s", async (_label, act) => {
    const store = await freshStore();
    store.openSheet(notebook, "text");
    store.setText("abc");
    store.showDraft(draft, "en");
    act(store);
    expect(window.sessionStorage.getItem(KEY)).toBeNull();
    expect(store.getCaptureState().text).toBe("");
  });

  it("keeps a long text in full", async () => {
    const long = "x".repeat(12000);
    window.sessionStorage.setItem(KEY, long);
    const store = await freshStore();
    expect(store.getCaptureState().text).toHaveLength(12000);
    store.setText(`${long}y`);
    expect(window.sessionStorage.getItem(KEY)).toHaveLength(12001);
  });

  it("works in memory when storage is blocked", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const store = await freshStore();
    expect(store.getCaptureState().text).toBe("");
    expect(() => store.setText("abc")).not.toThrow();
    expect(store.getCaptureState().text).toBe("abc");
  });
});
