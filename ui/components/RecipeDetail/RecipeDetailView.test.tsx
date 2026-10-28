/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { recipeFixture } from "./fixtures";
import { RecipeDetailView } from "./RecipeDetailView";

describe("RecipeDetailView", () => {
  let container: HTMLDivElement;
  let root: Root;
  const onDelete = vi.fn();

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    onDelete.mockReset();
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  function render(recipe = recipeFixture(), locale: "en" | "es" = "en") {
    act(() => {
      root.render(
        <RecipeDetailView
          recipe={recipe}
          locale={locale}
          backHref="/notebooks/nb1?page=2"
          editHref="/recipes/r1/edit?from=x"
          onDelete={onDelete}
        />,
      );
    });
  }

  it("shows the title, servings, author, notebook, every line and every step in order", () => {
    render();
    expect(container.querySelector("h1")?.textContent).toBe("Tomato rice");
    expect(container.textContent).toContain("4 servings");
    expect(container.textContent).toContain("ana");
    expect(container.textContent).toContain("ana's Notebook");
    const cards = Array.from(container.querySelectorAll("ul > li")).map((li) => li.textContent);
    expect(cards).toEqual([
      "rice1 cup",
      "onion2 largePreparation:chopped",
      "saltNote:to taste",
    ]);
    const steps = Array.from(container.querySelectorAll("ol > li")).map((li) => li.textContent);
    expect(steps).toEqual(["1Fry the garlic.", "2Add the rice."]);
  });

  it("is display only: no fields, dropdowns, or move and remove controls", () => {
    render();
    expect(container.querySelector("input, textarea, select")).toBeNull();
    const labels = Array.from(container.querySelectorAll("button")).map((b) => b.textContent);
    expect(labels).toEqual(["Delete"]);
    expect(container.querySelector("[aria-label=Remove]")).toBeNull();
    expect(container.querySelector("[aria-label='Move up']")).toBeNull();
    expect(container.querySelector("[aria-label='Move down']")).toBeNull();
  });

  it("badges estimated servings only when estimated", () => {
    render();
    expect(container.textContent).not.toContain("estimated");
    render(recipeFixture({ servings_estimated: true }));
    expect(container.textContent).toContain("estimated");
  });

  it("reads unknown for a gone author", () => {
    render(recipeFixture({ author_alias: null }));
    expect(container.textContent).toContain("unknown");
  });

  it("shows a source link only when the recipe has a url", () => {
    render();
    expect(container.querySelector("a[target=_blank]")).toBeNull();
    render(recipeFixture({ source: { type: "url", url: "https://example.com/soup" } }));
    expect(container.querySelector("a[target=_blank]")?.getAttribute("href")).toBe(
      "https://example.com/soup",
    );
  });

  it("goes back to the list it came from", () => {
    render();
    expect(container.querySelector("a[aria-label=Back]")?.getAttribute("href")).toBe(
      "/notebooks/nb1?page=2",
    );
  });

  it("offers Edit and Delete to those who can write", () => {
    render();
    const edit = Array.from(container.querySelectorAll("a")).find((a) => a.textContent === "Edit");
    expect(edit?.getAttribute("href")).toBe("/recipes/r1/edit?from=x");
    const del = Array.from(container.querySelectorAll("button")).find(
      (b) => b.textContent === "Delete",
    );
    act(() => del?.click());
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it("hides Edit and Delete when the member can only read", () => {
    render(recipeFixture({ can_write: false }));
    expect(container.textContent).not.toContain("Edit");
    expect(container.textContent).not.toContain("Delete");
  });

  it("speaks Spanish when asked", () => {
    render(recipeFixture(), "es");
    expect(container.textContent).toContain("Ingredientes");
    expect(container.textContent).toContain("Pasos");
  });
});
