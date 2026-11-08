import { beforeEach, describe, expect, it } from "vitest";

import {
  backToSheet,
  clearCapture,
  discardDraft,
  failSubmit,
  getCaptureState,
  openSheet,
  setHandwritten,
  setPicture,
  showDraft,
  type CaptureNotebook,
  type DraftView,
} from "./captureStore";

const notebook: CaptureNotebook = {
  id: "nb-1",
  kind: "personal",
  name: "Ana's Notebook",
  kitchenId: null,
  returnPath: "/notebooks/nb-1",
};

function draft(overrides: Partial<DraftView> = {}): DraftView {
  return {
    title: "Soup",
    baseServings: 4,
    servingsEstimated: false,
    lines: [],
    steps: [],
    catalog: [],
    ...overrides,
  };
}

function picture(name = "page.jpg"): File {
  return new File(["bytes"], name, { type: "image/jpeg" });
}

beforeEach(() => {
  clearCapture();
});

describe("the picture source", () => {
  it("opens the picture sheet with no file and the switch on", () => {
    openSheet(notebook, "picture");
    const { source, sheetOpen } = getCaptureState();
    expect(sheetOpen).toBe(true);
    expect(source).toEqual({ kind: "picture", file: null, handwritten: true });
  });

  it("keeps the chosen file and removes it on setPicture(null)", () => {
    openSheet(notebook, "picture");
    const file = picture();
    setPicture(file);
    expect(getCaptureState().source).toMatchObject({ kind: "picture", file });
    setPicture(null);
    expect(getCaptureState().source).toMatchObject({ kind: "picture", file: null });
  });

  it("keeps the file when the switch changes", () => {
    openSheet(notebook, "picture");
    const file = picture();
    setPicture(file);
    setHandwritten(false);
    expect(getCaptureState().source).toEqual({ kind: "picture", file, handwritten: false });
  });

  it("keeps the flag on a picture draft", () => {
    openSheet(notebook, "picture");
    setPicture(picture());
    showDraft(draft({ fromPicture: true }), "en");
    expect(getCaptureState().draft?.fromPicture).toBe(true);
  });

  it("Back returns to the picture sheet with the same file and the same switch", () => {
    openSheet(notebook, "picture");
    const file = picture();
    setPicture(file);
    setHandwritten(false);
    showDraft(draft({ fromPicture: true }), "en");
    backToSheet();
    const state = getCaptureState();
    expect(state.sheetOpen).toBe(true);
    expect(state.source).toEqual({ kind: "picture", file, handwritten: false });
  });

  it("Discard empties the file and keeps the switch", () => {
    openSheet(notebook, "picture");
    setPicture(picture());
    setHandwritten(false);
    showDraft(draft({ fromPicture: true }), "en");
    discardDraft();
    expect(getCaptureState().source).toEqual({ kind: "picture", file: null, handwritten: false });
  });

  it("a failed submit keeps the file", () => {
    openSheet(notebook, "picture");
    const file = picture();
    setPicture(file);
    failSubmit({ code: "ai_unavailable" });
    expect(getCaptureState().source).toMatchObject({ kind: "picture", file });
  });

  it("clearCapture drops the file", () => {
    openSheet(notebook, "picture");
    setPicture(picture());
    clearCapture();
    expect(getCaptureState().source).toEqual({ kind: "text" });
  });

  it("choosing a file clears the last message", () => {
    openSheet(notebook, "picture");
    failSubmit({ code: "picture_unsupported" });
    setPicture(picture());
    expect(getCaptureState().message).toBeNull();
  });
});
