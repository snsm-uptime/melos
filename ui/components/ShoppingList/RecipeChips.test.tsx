/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { mount } from "@/components/Cart/testRoot";

import { RecipeChips } from "./RecipeChips";

describe("RecipeChips", () => {
  let view: ReturnType<typeof mount>;

  beforeEach(() => {
    view = mount();
  });
  afterEach(() => view.unmount());

  function anchors() {
    return Array.from(view.container.querySelectorAll("a"));
  }

  it("links each recipe to its page with the Cart page as the way back", () => {
    view.render(
      <RecipeChips
        kitchenId="k 1"
        locale="en"
        recipes={[
          { recipe_id: "r1", title: "Bread" },
          { recipe_id: "r/2", title: "Pancakes" },
        ]}
      />,
    );
    const from = encodeURIComponent("/kitchens/k%201/cart");
    expect(anchors().map((a) => a.getAttribute("href"))).toEqual([
      `/recipes/r1?from=${from}`,
      `/recipes/r%2F2?from=${from}`,
    ]);
    expect(anchors().map((a) => a.textContent)).toEqual(["Bread", "Pancakes"]);
  });

  it("names the group and keeps the full title on each chip", () => {
    view.render(
      <RecipeChips
        kitchenId="k1"
        locale="en"
        recipes={[{ recipe_id: "r1", title: "A very long title for a small chip" }]}
      />,
    );
    expect(view.container.querySelector("ul")?.getAttribute("aria-label")).toBe("Recipes");
    expect(anchors()[0].getAttribute("title")).toBe("A very long title for a small chip");
  });

  it("names the group in Spanish", () => {
    view.render(
      <RecipeChips kitchenId="k1" locale="es" recipes={[{ recipe_id: "r1", title: "Pan" }]} />,
    );
    expect(view.container.querySelector("ul")?.getAttribute("aria-label")).toBe("Recetas");
  });

  it("shows two recipes with the same title as two chips", () => {
    view.render(
      <RecipeChips
        kitchenId="k1"
        locale="en"
        recipes={[
          { recipe_id: "r1", title: "Soup" },
          { recipe_id: "r2", title: "Soup" },
        ]}
      />,
    );
    expect(anchors()).toHaveLength(2);
  });

  it("makes each chip a touch target of at least 44px", () => {
    view.render(
      <RecipeChips kitchenId="k1" locale="en" recipes={[{ recipe_id: "r1", title: "Bread" }]} />,
    );
    expect(anchors()[0].className).toContain("min-h-11");
  });

  it("shows a saved chip whose recipe is gone as plain text", () => {
    view.render(
      <RecipeChips
        kitchenId="k1"
        locale="en"
        recipes={[{ recipe_id: "r1", title: "Bread", exists: false }]}
      />,
    );
    expect(anchors()).toEqual([]);
    expect(view.container.textContent).toContain("Bread");
  });
});
