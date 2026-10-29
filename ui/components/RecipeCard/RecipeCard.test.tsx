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

  it("links to the recipe detail with the list it is on", () => {
    render({ from: "/notebooks/n1?page=2&q=soup" });
    const link = container.querySelector("a");
    expect(link?.textContent).toBe("Lentil soup");
    expect(link?.getAttribute("href")).toBe(
      `/recipes/r1?from=${encodeURIComponent("/notebooks/n1?page=2&q=soup")}`,
    );
  });

  it("links the notebook name to its notebook, apart from the card's own link", () => {
    render({ showNotebook: true, from: "/kitchens/k1" });
    const links = Array.from(container.querySelectorAll("a"));
    expect(links.map((a) => a.textContent)).toEqual(["Lentil soup", "ana's (Home) Notebook"]);
    // The list the card is on travels along, so the notebook's Back returns to it.
    expect(links[1].getAttribute("href")).toBe(`/notebooks/n1?from=${encodeURIComponent("/kitchens/k1")}`);
    // Always underlined, accent colour on hover.
    expect(links[1].className).toContain("underline");
    expect(links[1].className).not.toContain("hover:underline");
    expect(links[1].className).toContain("hover:text-accent");
  });

  it("shows the notebook name as plain text on a card that is not a link", () => {
    render({ showNotebook: true });
    expect(container.querySelector("a")).toBeNull();
    expect(container.textContent).toContain("ana's (Home) Notebook");
  });

  it("shows the whole card as the link's target, and only when it is a link", () => {
    render({ from: "/kitchens/k1" });
    const article = container.querySelector("article") as HTMLElement;
    expect(article.className).toContain("cursor-pointer");
    expect(article.className).toContain("hover:border-accent");
    // The title link's overlay covers the card (its ::after is positioned against the article).
    expect(article.className).toContain("relative");
    expect(container.querySelector("h3 a")?.className).toContain("after:inset-0");

    render();
    expect((container.querySelector("article") as HTMLElement).className).not.toContain("cursor-pointer");
  });

  it("is not a link without a list to return to", () => {
    render();
    expect(container.querySelector("a")).toBeNull();
  });

  it("in Spanish the interface words change and the recipe's own words do not (spec 063 FR-008)", () => {
    render({ locale: "es", recipe: { ...recipe, author_alias: null, ingredient_count: 1 } });
    const text = container.textContent ?? "";
    expect(text).toContain("desconocido");
    expect(text).toContain("1 ingrediente");
    expect(text).toContain("Lentil soup");
    expect(text).not.toContain("unknown");
  });

  it("shows the cart-icon button only when given, and tapping calls back", () => {
    let toggled = 0;
    render({ cart: { inCart: false, onToggle: () => (toggled += 1) } });
    const button = container.querySelector<HTMLButtonElement>("button")!;
    expect(button.getAttribute("aria-label")).toBe("Add to cart");
    expect(button.getAttribute("aria-pressed")).toBe("false");
    expect(button.disabled).toBe(false);
    act(() => button.click());
    expect(toggled).toBe(1);
  });

  it("reads Remove from cart, pressed, with the plus turned, when in the cart", () => {
    render({ cart: { inCart: true, onToggle: () => {} } });
    const button = container.querySelector<HTMLButtonElement>("button")!;
    expect(button.getAttribute("aria-label")).toBe("Remove from cart");
    expect(button.getAttribute("aria-pressed")).toBe("true");
    const mark = container.querySelector<SVGGElement>("[data-testid=cart-plus-mark]")!;
    expect(mark.style.transform).toBe("rotate(45deg)");
  });
});
