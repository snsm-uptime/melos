/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { RecipeCard as RecipeCardData } from "@/lib/recipesClient";

import { RecipeCard } from "./RecipeCard";

const recipe: RecipeCardData = {
  id: "r1",
  title: "Lentil soup",
  author_alias: "ana",
  ingredient_count: 7,
  notebook_id: "n1",
  notebook_name: "ana's (Home) Notebook",
  created_at: "2026-10-27T12:00:00Z",
};

describe("RecipeCard", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  function render(props: Partial<Parameters<typeof RecipeCard>[0]> = {}) {
    act(() => {
      root.render(<RecipeCard recipe={recipe} locale="en" {...props} />);
    });
  }

  it("shows the pot icon, title, author chip and ingredient count", () => {
    render();
    expect(container.querySelector("[data-testid=recipe-pot-icon]")).not.toBeNull();
    expect(container.textContent).toContain("Lentil soup");
    expect(container.textContent).toContain("ana");
    expect(container.textContent).toContain("7 ingredients");
  });

  it("has no link, button or checkbox", () => {
    render();
    expect(container.querySelector("a, button, input")).toBeNull();
  });

  it("shows the notebook name only when asked", () => {
    render();
    expect(container.textContent).not.toContain("Home");
    render({ showNotebook: true });
    expect(container.textContent).toContain("ana's (Home) Notebook");
  });

  it("reads unknown for a missing author and uses the singular for one ingredient", () => {
    render({ recipe: { ...recipe, author_alias: null, ingredient_count: 1 } });
    expect(container.textContent).toContain("unknown");
    expect(container.textContent).toContain("1 ingredient");
    expect(container.textContent).not.toContain("1 ingredients");
  });

  it("keeps the full title in the tooltip", () => {
    render({ recipe: { ...recipe, title: "A very long title ".repeat(10) } });
    expect(container.querySelector("h3")?.getAttribute("title")).toContain("A very long title");
  });
});
