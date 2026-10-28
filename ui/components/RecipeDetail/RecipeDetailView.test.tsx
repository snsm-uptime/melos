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

  const servingsInput = () => container.querySelector("input") as HTMLInputElement;
  const cards = () => Array.from(container.querySelectorAll("ul > li")).map((li) => li.textContent);
  const stepsText = () => Array.from(container.querySelectorAll("ol > li")).map((li) => li.textContent);

  function setServings(value: string) {
    const input = servingsInput();
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, value);
    act(() => {
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }
  const button = (label: string) =>
    Array.from(container.querySelectorAll("button")).find(
      (b) => (b.getAttribute("aria-label") ?? b.textContent) === label,
    );

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
    expect(servingsInput().value).toBe("4");
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

  it("is display only apart from the servings: no other fields, dropdowns, or move and remove controls", () => {
    render();
    const fields = Array.from(container.querySelectorAll("input, textarea, select"));
    expect(fields).toEqual([servingsInput()]);
    const labels = Array.from(container.querySelectorAll("button")).map(
      (b) => b.getAttribute("aria-label") ?? b.textContent,
    );
    expect(labels).toEqual(["Fewer servings", "More servings", "Delete"]);
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

  // --- spec 062: scale the servings (view only) ---

  describe("servings", () => {
    it("scales measured and counted amounts in proportion", () => {
      render();
      setServings("8");
      expect(cards()[0]).toBe("rice2 cup");
      expect(cards()[1]).toBe("onion4 largePreparation:chopped");
      setServings("2");
      expect(cards()[0]).toBe("rice0.5 cup");
      setServings("6");
      expect(cards()[0]).toBe("rice1.5 cup");
      expect(cards()[1]).toContain("3 large");
      setServings("5");
      expect(cards()[1]).toContain("2.5 large");
    });

    it("leaves the vague note, preparation, units and order alone", () => {
      render();
      setServings("6");
      expect(cards()).toEqual([
        "rice1.5 cup",
        "onion3 largePreparation:chopped",
        "saltNote:to taste",
      ]);
    });

    it("scales an estimated recipe from the same saved number and keeps the badge", () => {
      render(recipeFixture({ servings_estimated: true }));
      expect(container.textContent).toContain("estimated");
      setServings("8");
      expect(cards()[0]).toBe("rice2 cup");
      expect(container.textContent).toContain("Makes 4");
      expect(container.textContent).toContain("estimated");
    });

    it("never shows an amount above zero as 0", () => {
      const base = recipeFixture();
      render(
        recipeFixture({
          ingredient_lines: [{ ...base.ingredient_lines[0], name: "saffron", quantity: 0.01, unit: "tsp" }],
        }),
      );
      setServings("1");
      expect(cards()[0]).toBe("saffron<0.01 tsp");
    });

    it("updates every amount of a recipe of 100 lines", () => {
      const base = recipeFixture().ingredient_lines[0];
      render(
        recipeFixture({
          ingredient_lines: Array.from({ length: 100 }, (_, n) => ({
            ...base,
            name: `item${n}`,
            quantity: n + 1,
          })),
        }),
      );
      setServings("8");
      const shown = cards();
      expect(shown).toHaveLength(100);
      expect(shown[0]).toBe("item02 cup");
      expect(shown[99]).toBe("item99200 cup");
    });

    it("leaves the step texts alone and says so only while the servings differ", () => {
      render();
      const before = stepsText();
      expect(container.textContent).not.toContain("Steps show the recipe as saved.");
      setServings("6");
      expect(stepsText()).toEqual(before);
      expect(container.textContent).toContain("Steps show the recipe as saved.");
    });

    it("does not apply an invalid entry and shows the hint", () => {
      render();
      setServings("6");
      for (const bad of ["abc", "0", "101", "2.5", ""]) {
        setServings(bad);
        expect(cards()[0]).toBe("rice1.5 cup");
        expect(container.querySelector("[role=alert]")?.textContent).toBe(
          "Enter a whole number from 1 to 100.",
        );
      }
    });

    it("has no English interface text in Spanish, and shows stored text as stored", () => {
      render(recipeFixture(), "es");
      const text = container.textContent ?? "";
      for (const expected of ["Ingredientes", "Pasos", "Preparación:", "Nota:", "Editar", "Eliminar", "Porciones"]) {
        expect(text, expected).toContain(expected);
      }
      expect(text).not.toMatch(/\b(Ingredients|Steps|Preparation|Note|Edit|Delete|Servings)\b/);
      expect(container.querySelector("[aria-label=Volver]")).not.toBeNull();
      // The recipe's own words are not translated (FR-008).
      expect(text).toContain("Tomato rice");
      expect(text).toContain("chopped");
      expect(text).toContain("to taste");
      expect(text).toContain("Fry the garlic.");
    });

    it("speaks Spanish", () => {
      render(recipeFixture(), "es");
      expect(container.querySelector("label")?.textContent).toBe("Porciones");
      setServings("6");
      expect(container.textContent).toContain("Los pasos muestran la receta como se guardó.");
      expect(container.textContent).toContain("Rinde 4");
    });
  });

  // --- spec 062 US2: the change is only a view ---

  describe("the change is only a view", () => {
    it("sends nothing, stores nothing, sets no cookie and does not touch the recipe", () => {
      const fetchSpy = vi.fn();
      vi.stubGlobal("fetch", fetchSpy);
      const setItem = vi.spyOn(Storage.prototype, "setItem");
      const cookie = vi.spyOn(document, "cookie", "set");
      const recipe = recipeFixture();
      const frozen = JSON.parse(JSON.stringify(recipe));
      deepFreeze(recipe);
      render(recipe);

      setServings("6");
      act(() => button("More servings")?.click());
      act(() => button("Fewer servings")?.click());

      expect(fetchSpy).not.toHaveBeenCalled();
      expect(setItem).not.toHaveBeenCalled();
      expect(cookie).not.toHaveBeenCalled();
      expect(JSON.parse(JSON.stringify(recipe))).toEqual(frozen);
      setItem.mockRestore();
      cookie.mockRestore();
      vi.unstubAllGlobals();
    });

    it("starts again from the saved servings when the page is shown again", () => {
      render();
      setServings("6");
      expect(cards()[0]).toBe("rice1.5 cup");
      act(() => root.unmount());
      root = createRoot(container);
      render();
      expect(servingsInput().value).toBe("4");
      expect(cards()[0]).toBe("rice1 cup");
    });

    it("gives Edit the same link whatever the servings", () => {
      render();
      const edit = () =>
        Array.from(container.querySelectorAll("a"))
          .find((a) => a.textContent === "Edit")
          ?.getAttribute("href");
      const before = edit();
      setServings("6");
      expect(edit()).toBe(before);
      expect(edit()).not.toMatch(/serving/i);
    });

    it("works for a member who can only read", () => {
      render(recipeFixture({ can_write: false }));
      setServings("6");
      expect(cards()[0]).toBe("rice1.5 cup");
      expect(container.textContent).not.toContain("Edit");
      expect(container.textContent).not.toContain("Delete");
    });
  });

  // --- spec 062 US3: reset and the saved servings ---

  describe("reset", () => {
    it("offers neither Makes nor Reset at the saved servings", () => {
      render();
      expect(container.textContent).not.toContain("Makes");
      expect(button("Reset")).toBeUndefined();
    });

    it("states the saved servings and resets to them in one action", () => {
      render();
      setServings("7");
      expect(container.textContent).toContain("Makes 4");
      act(() => button("Reset")?.click());
      expect(servingsInput().value).toBe("4");
      expect(cards()[0]).toBe("rice1 cup");
      expect(container.textContent).not.toContain("Makes");
      expect(button("Reset")).toBeUndefined();
      expect(container.textContent).not.toContain("Steps show the recipe as saved.");
    });

    it("hides Reset when the saved number is typed by hand", () => {
      render();
      setServings("7");
      setServings("4");
      expect(button("Reset")).toBeUndefined();
      expect(container.textContent).not.toContain("Makes");
    });
  });
});

function deepFreeze<T>(value: T): T {
  if (value && typeof value === "object") {
    Object.values(value).forEach(deepFreeze);
    Object.freeze(value);
  }
  return value;
}
