import { beforeEach, describe, expect, it } from "vitest";

import {
  NEW_CHOICE,
  chooseLineMatch,
  chooseMatch,
  clearCapture,
  getCaptureState,
  showDraft,
  undoChange,
  undoLineChange,
  type DraftView,
  type LineView,
} from "./captureStore";

function matchedOnion(): LineView {
  return {
    key: "l1",
    name: "onion",
    vague: false,
    quantity: 2,
    unit: "unit",
    size: "large",
    preparation: null,
    note: null,
    textName: "onions",
    match: { kind: "matched", entry: "onion" },
  };
}

const draft: DraftView = {
  title: "Onion soup",
  baseServings: 4,
  servingsEstimated: false,
  mainIngredients: [],
  cuisines: [],
  lines: [matchedOnion()],
  steps: [{ key: "s1", text: "Simmer." }],
  catalog: ["onion", "spring onion"],
};

beforeEach(() => clearCapture());

describe("undoLineChange", () => {
  it("returns the line to new ingredient with the name the text wrote", () => {
    expect(undoLineChange(matchedOnion())).toMatchObject({
      name: "onions",
      match: { kind: "new", entry: null },
    });
  });
});

describe("chooseLineMatch", () => {
  it("sets the match and the name to the chosen catalog entry", () => {
    expect(chooseLineMatch(matchedOnion(), "spring onion")).toMatchObject({
      name: "spring onion",
      match: { kind: "matched", entry: "spring onion" },
    });
  });

  it("choosing new ingredient returns the line to its text name", () => {
    expect(chooseLineMatch(matchedOnion(), NEW_CHOICE)).toMatchObject({
      name: "onions",
      match: { kind: "new", entry: null },
    });
  });
});

describe("store actions on one line", () => {
  it("undoChange changes only the chosen line", () => {
    showDraft({ ...draft, lines: [matchedOnion(), { ...matchedOnion(), key: "l2", textName: "flour", name: "flour" }] }, "en");

    undoChange(0);

    const [first, second] = getCaptureState().draft!.lines;
    expect(first.match.kind).toBe("new");
    expect(first.name).toBe("onions");
    expect(second.name).toBe("flour");
  });

  it("chooseMatch replaces the match of the chosen line", () => {
    showDraft(draft, "en");

    chooseMatch(0, "spring onion");

    expect(getCaptureState().draft!.lines[0]).toMatchObject({
      name: "spring onion",
      match: { kind: "matched", entry: "spring onion" },
    });
  });
});
