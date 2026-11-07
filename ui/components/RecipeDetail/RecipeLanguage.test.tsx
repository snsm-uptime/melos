/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { RecipeDetail } from "@/lib/recipesClient";
import { toEditState, toUpdateBody } from "@/lib/recipeEdit";

import { recipeFixture } from "./fixtures";
import { RecipeDetailView } from "./RecipeDetailView";

/** A Spanish recipe whose "onion" line shows its Spanish name (spec 043 FR-006). */
function spanish(overrides: Partial<RecipeDetail> = {}): RecipeDetail {
  const base = recipeFixture();
  return recipeFixture({
    language: "es",
    proposed_language: null,
    ingredient_lines: base.ingredient_lines.map((line) =>
      line.name === "onion" ? { ...line, shown_name: "cebolla" } : { ...line, shown_name: line.name },
    ),
    ...overrides,
  });
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("recipe language (spec 043)", () => {
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
    vi.unstubAllGlobals();
  });

  function render(recipe: RecipeDetail, onRecipeChange = vi.fn()) {
    act(() => {
      root.render(
        <RecipeDetailView
          recipe={recipe}
          locale="en"
          backHref="/notebooks/nb1"
          editHref="/recipes/r1/edit"
          onDelete={() => {}}
          onRecipeChange={onRecipeChange}
        />,
      );
    });
    return onRecipeChange;
  }

  const button = (text: string) =>
    Array.from(container.querySelectorAll("button")).find((b) => b.textContent === text);

  it("shows each line in the recipe's language and names the language", () => {
    render(spanish());
    const cards = Array.from(container.querySelectorAll("ul > li")).map((li) => li.textContent);
    expect(cards[1]).toContain("cebolla");
    expect(cards[1]).not.toContain("onion");
    expect(container.textContent).toContain("Language");
    expect(container.textContent).toContain("Spanish");
    expect(container.textContent).not.toContain("Detected:");
  });

  it("offers a detected language and applies it", async () => {
    const applied = spanish({ language: "en", proposed_language: null });
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(applied), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const changed = render(spanish({ proposed_language: "en" }));

    expect(container.textContent).toContain("Detected: English. Apply?");
    await act(async () => {
      button("Apply")!.click();
      await flush();
    });

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/recipes/r1/language");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(String(init.body))).toEqual({ language: "en" });
    expect(changed).toHaveBeenCalledWith(applied);
  });

  it("dismisses the proposal without changing the language", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(spanish()), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(spanish({ proposed_language: "en" }));
    await act(async () => {
      button("Dismiss")!.click();
      await flush();
    });
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toEqual({ language: null });
  });

  it("hides the proposal from a person who can only read", () => {
    render(spanish({ proposed_language: "en", can_write: false }));
    expect(container.textContent).not.toContain("Detected:");
  });

  it("edits with the shown names and sends the chosen language", () => {
    const state = toEditState(spanish());
    expect(state.language).toBe("es");
    expect(state.lines[1].name).toBe("cebolla");
    const body = toUpdateBody({ ...state, language: "en" }, "v1");
    expect(body.language).toBe("en");
    expect(body.ingredient_lines[1].name).toBe("cebolla");
  });
});
