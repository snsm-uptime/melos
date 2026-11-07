/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { recipeFixture } from "./fixtures";
import { RecipeDetailView } from "./RecipeDetailView";

const chrome = vi.hoisted(() => ({ scrolled: false }));
vi.mock("@/components/ChromeScroll", () => ({ useChromeScrolled: () => chrome.scrolled }));

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

  /** Edit, Share and Delete live in the chrome's dots menu. */
  function openMenu(label = "Recipe options") {
    act(() => button(label)?.click());
  }

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

  it("the page header is a frosted phone bar with no solid background", async () => {
    render();
    const header = container.querySelector("header") as HTMLElement;
    expect(header.classList.contains("frost-bar")).toBe(true);
    expect(header.classList.contains("frost-bar-phone")).toBe(true);
    expect(header.classList.contains("bg-background")).toBe(false);
    expect(header.getAttribute("data-frosted")).toBe("false");
  });

  it("frosts the page header once the main scroller has been scrolled", async () => {
    chrome.scrolled = true;
    try {
      render();
      expect(container.querySelector("header")?.getAttribute("data-frosted")).toBe("true");
    } finally {
      chrome.scrolled = false;
    }
  });

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
      "saltto tasteNote:Use sea salt",
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
    // Edit, Share and Delete wait in the dots menu; the rest are the servings.
    expect(labels).toEqual(["Recipe options", "Fewer servings", "More servings"]);
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

  it("shows the source as a link icon in the chrome only when the recipe has a url", () => {
    render();
    expect(container.querySelector("a[target=_blank]")).toBeNull();
    render(recipeFixture({ source: { type: "url", url: "https://example.com/soup" } }));
    const link = container.querySelector("header a[target=_blank]");
    expect(link?.getAttribute("href")).toBe("https://example.com/soup");
    expect(link?.getAttribute("aria-label")).toBe("Source");
    expect(link?.querySelector("svg")).not.toBeNull();
  });

  it("opens the source page in a new tab that cannot reach back (spec 026)", () => {
    render(recipeFixture({ source: { type: "url", url: "https://example.com/soup" } }));

    const link = container.querySelector("a[target=_blank]");
    expect(link?.getAttribute("rel")).toBe("noopener noreferrer");
  });

  it("shows the recipe image at the top only when it has one (spec 026)", () => {
    render();
    expect(container.querySelector("img")).toBeNull();

    render(recipeFixture({ preview_image: "data:image/jpeg;base64,AAAA" }));

    const img = container.querySelector("img");
    expect(img?.getAttribute("src")).toBe("data:image/jpeg;base64,AAAA");
    expect(img?.getAttribute("alt")).toBe("Tomato rice");
  });

  it("goes back to the list it came from", () => {
    render();
    expect(container.querySelector("a[aria-label=Back]")?.getAttribute("href")).toBe(
      "/notebooks/nb1?page=2",
    );
  });

  it("offers Edit, Share and Delete in the dots menu to those who can write", () => {
    render();
    expect(container.textContent).not.toContain("Edit");
    openMenu();
    const items = Array.from(container.querySelectorAll("[role=menuitem]")).map((i) => i.textContent);
    expect(items).toEqual(["Edit", "Share recipe", "Delete"]);
    for (const item of container.querySelectorAll("[role=menuitem]")) {
      expect(item.firstElementChild?.querySelector("svg"), item.textContent ?? "").not.toBeNull();
    }
    const edit = Array.from(container.querySelectorAll("a")).find((a) => a.textContent === "Edit");
    expect(edit?.getAttribute("href")).toBe("/recipes/r1/edit?from=x");
    const del = Array.from(container.querySelectorAll("button")).find(
      (b) => b.textContent === "Delete",
    );
    act(() => del?.click());
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it("keeps only Share in the menu when the member can only read (spec 071 FR-001)", () => {
    render(recipeFixture({ can_write: false }));
    openMenu();
    const items = Array.from(container.querySelectorAll("[role=menuitem]")).map((i) => i.textContent);
    expect(items).toEqual(["Share recipe"]);
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
        "saltto tasteNote:Use sea salt",
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
      openMenu("Opciones de la receta");
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
      openMenu();
      const before = edit();
      expect(before).toBe("/recipes/r1/edit?from=x");
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

  describe("edit lock and cart (spec 022)", () => {
    it("disables Edit and Delete and names the editor while someone else edits", () => {
      render(recipeFixture({ editor: { alias: "ben", is_me: false, idle_expires_at: null } }));
      expect(container.textContent).toContain("ben is editing this recipe");
      openMenu();
      expect(button("Delete")?.disabled).toBe(true);
      expect(button("Edit")?.disabled).toBe(true);
      expect(container.querySelector('a[href="/recipes/r1/edit?from=x"]')).toBeNull();
    });

    it("keeps Edit open for my own lock", () => {
      render(
        recipeFixture({ editor: { alias: "ana", is_me: true, idle_expires_at: "2999-01-01T00:00:00Z" } }),
      );
      openMenu();
      expect(container.querySelector('a[href="/recipes/r1/edit?from=x"]')).not.toBeNull();
      expect(container.textContent).not.toContain("is editing this recipe");
    });

    it("shows the cart-icon button, which toggles and is never disabled", () => {
      const onToggle = vi.fn();
      const show = (inCart: boolean) =>
        act(() => {
          root.render(
            <RecipeDetailView
              recipe={recipeFixture()}
              locale="en"
              backHref="/x"
              editHref="/e"
              onDelete={onDelete}
              cartAction={{ inCart, onToggle }}
            />,
          );
        });
      show(false);
      act(() => button("Add to cart")?.click());
      expect(onToggle).toHaveBeenCalled();
      show(true);
      const remove = button("Remove from cart");
      expect(remove?.disabled).toBe(false);
      expect(remove?.getAttribute("aria-pressed")).toBe("true");
    });

    it("has no cart button without the cart action", () => {
      render();
      expect(button("Add to cart")).toBeUndefined();
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
