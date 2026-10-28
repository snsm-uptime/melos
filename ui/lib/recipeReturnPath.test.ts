import { describe, expect, it } from "vitest";

import { notebookBackPath, safeReturnPath } from "./recipeReturnPath";

describe("safeReturnPath", () => {
  it("keeps notebook and kitchen paths, with their queries", () => {
    expect(safeReturnPath("/notebooks/n1?page=2&q=soup", "nb")).toBe("/notebooks/n1?page=2&q=soup");
    expect(safeReturnPath("/kitchens/k1", "nb")).toBe("/kitchens/k1");
  });

  it.each([
    "https://evil.example/notebooks/x",
    "//evil.example",
    "/\\evil",
    "/account",
    "/notebooks//evil",
    "/notebooks/a:b",
    "/notebooks/a b",
    "notebooks/n1",
    "",
  ])("falls back for %s", (from) => {
    expect(safeReturnPath(from, "nb")).toBe("/notebooks/nb");
  });

  it("falls back for null and undefined", () => {
    expect(safeReturnPath(null, "nb")).toBe("/notebooks/nb");
    expect(safeReturnPath(undefined, "nb")).toBe("/notebooks/nb");
  });
});

describe("notebookBackPath", () => {
  it("goes back to the kitchen or notebook list it was opened from", () => {
    expect(notebookBackPath("/kitchens/k1?page=2")).toBe("/kitchens/k1?page=2");
    expect(notebookBackPath("/notebooks/n2")).toBe("/notebooks/n2");
  });

  it.each([null, undefined, "", "/account", "https://evil.example/kitchens/k1", "//evil.example"])(
    "falls back to the Notebook tab for %s",
    (from) => {
      expect(notebookBackPath(from)).toBe("/notebooks");
    },
  );
});
