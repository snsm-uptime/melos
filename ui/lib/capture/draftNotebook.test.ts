import { afterEach, describe, expect, it } from "vitest";

import {
  clearCapture,
  getCaptureState,
  openSheet,
  OWN_NEW_NOTEBOOK_ID,
  setDraftNotebook,
  startManualDraft,
} from "./captureStore";

const home = { id: "p1", kind: "personal" as const, name: "Mine", kitchenId: null };
const weekend = { id: "p2", kind: "personal" as const, name: "Weekend", kitchenId: null };
const ownNew = { id: OWN_NEW_NOTEBOOK_ID, kind: "kitchen" as const, name: "Mine (new)", kitchenId: "k1" };

afterEach(() => clearCapture());

describe("the manual draft's notebook", () => {
  it("moves to another notebook and keeps where Back returns", () => {
    startManualDraft({ ...home, returnPath: "/kitchens/k1" }, "en", [home, weekend]);
    setDraftNotebook(weekend);
    expect(getCaptureState().notebook).toMatchObject({ id: "p2", returnPath: "/kitchens/k1" });
  });

  it("swaps the new-notebook row for the notebook made for it", () => {
    startManualDraft({ ...home, returnPath: "/notebooks" }, "en", [home, ownNew]);
    setDraftNotebook({ ...ownNew, id: "kn1", name: "Mine (Home)" });
    expect(getCaptureState().notebookChoices.map((item) => item.id)).toEqual(["p1", "kn1"]);
  });

  it("has no choices for a captured draft", () => {
    startManualDraft({ ...home, returnPath: "/notebooks" }, "en", [home, weekend]);
    openSheet({ ...home, returnPath: "/notebooks" }, "text");
    expect(getCaptureState().notebookChoices).toEqual([]);
  });
});
