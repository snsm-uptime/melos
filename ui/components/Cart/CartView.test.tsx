/** @vitest-environment jsdom */

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CartView, draftFromCart, type LocalDraft } from "./CartView";
import { cart, entry, mount, type } from "./testRoot";

function buttons(container: HTMLElement) {
  return Array.from(container.querySelectorAll("button")).map((b) => b.textContent);
}

function click(container: HTMLElement, label: string) {
  const button = Array.from(container.querySelectorAll("button")).find(
    (b) => b.textContent === label,
  );
  act(() => button?.click());
}

describe("CartView", () => {
  let view: ReturnType<typeof mount>;
  const handlers = {
    onDraftChange: vi.fn(),
  };

  beforeEach(() => {
    view = mount();
    for (const fn of Object.values(handlers)) fn.mockReset();
  });
  afterEach(() => view.unmount());

  function render(props: Partial<Parameters<typeof CartView>[0]> = {}) {
    view.render(
      <CartView
        cart={cart()}
        draft={null}
        kitchenId="k1"
        locale="en"
        dropped={0}
        {...handlers}
        {...props}
      />,
    );
  }

  it("shows the empty hint with a link to the notebooks", () => {
    render();
    expect(view.container.textContent).toContain("Add recipes from the kitchen's notebooks");
    expect(view.container.querySelector('a[href="/kitchens/k1"]')).not.toBeNull();
    expect(view.container.textContent).not.toContain("People");
  });

  it("puts the empty hint first, with no Edit button in the page", () => {
    render();
    const first = view.container.querySelector("section")?.firstElementChild;
    expect(first?.textContent).toContain("Add recipes from the kitchen's notebooks");
    expect(buttons(view.container)).toEqual([]);
  });

  it("shows saved entries with notebook, base servings, servings and factor", () => {
    render({ cart: cart({ entries: [entry("a")] }) });
    const text = view.container.textContent ?? "";
    expect(text).toContain("Recipe a");
    expect(text).toContain("ana's (Home) Notebook");
    expect(text).toContain("Serves 4");
    expect(text).toContain("Servings 1");
    expect(text).toContain("×0.5");
    expect(view.container.querySelector('a[href^="/recipes/a?from="]')).not.toBeNull();
    expect(buttons(view.container)).toEqual([]);
  });

  it("disables everything and names the editor while someone else edits", () => {
    render({
      cart: cart({
        entries: [entry("a")],
        editor: { alias: "ben", is_me: false, idle_expires_at: null },
        can_edit: false,
      }),
    });
    expect(view.container.textContent).toContain("ben is editing the cart");
    expect(buttons(view.container)).toEqual([]);
    expect(view.container.querySelector("input")).toBeNull();
  });

  describe("editing", () => {
    const mine = cart({
      editor: { alias: "ana", is_me: true, idle_expires_at: "2999-01-01T00:00:00Z" },
      draft: {
        entries: [entry("a"), entry("b", { base_servings: 3 })],
        dropped_recipe_ids: [],
      },
    });
    const draft = draftFromCart(mine) as LocalDraft;

    it("recomputes factors live and sends the whole draft", () => {
      render({ cart: mine, draft });
      const factors = Array.from(view.container.querySelectorAll("[data-testid=factor]"));
      expect(factors.map((f) => f.textContent)).toEqual(["×0.25", "×0.33"]);
      const [servingsA] = Array.from(view.container.querySelectorAll("input"));
      type(servingsA, "2");
      expect(handlers.onDraftChange.mock.lastCall?.[0].entries[0].servings).toBe(2);
    });

    it("shows the factor of the new numbers", () => {
      render({ cart: mine, draft: { ...draft, entries: [entry("a", { servings: 6 })] } });
      expect(view.container.querySelector("[data-testid=factor]")?.textContent).toBe("×1.5");
    });

    it("removes an entry; Save and Discard live on the docked bar, not in the view", () => {
      render({ cart: mine, draft });
      const remove = view.container.querySelector('button[aria-label="Remove Recipe a"]');
      expect(remove?.textContent).not.toContain("Remove");
      act(() => (remove as HTMLButtonElement).click());
      expect(handlers.onDraftChange.mock.lastCall?.[0].entries.map((e: { recipe_id: string }) => e.recipe_id)).toEqual(["b"]);
      expect(buttons(view.container)).not.toContain("Save");
      expect(buttons(view.container)).not.toContain("Discard");
    });

    it("clears after confirmation", () => {
      render({ cart: mine, draft });
      click(view.container, "Clear");
      expect(document.body.textContent).toContain("Remove every recipe from the cart?");
      const confirm = Array.from(document.body.querySelectorAll("button")).filter(
        (b) => b.textContent === "Clear",
      );
      act(() => confirm[confirm.length - 1].click());
      expect(handlers.onDraftChange).toHaveBeenLastCalledWith({ ...draft, entries: [] });
    });

    it("shows the dropped-recipes banner", () => {
      render({ cart: mine, draft, dropped: 1 });
      expect(view.container.textContent).toContain("1 recipe was removed because it was deleted.");
    });
  });
});
