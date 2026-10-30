/** Shared mount helper for the Cart component tests (createRoot, as the other ui tests do). */

import { act, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";

import type { Cart, CartEntry } from "@/lib/cartClient";

export function mount() {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root: Root = createRoot(container);
  return {
    container,
    render(node: ReactNode) {
      act(() => root.render(node));
    },
    unmount() {
      act(() => root.unmount());
      container.remove();
    },
  };
}

export function entry(id: string, over: Partial<CartEntry> = {}): CartEntry {
  return {
    recipe_id: id,
    title: `Recipe ${id}`,
    notebook_id: "n1",
    notebook_name: "ana's (Home) Notebook",
    base_servings: 4,
    servings: 1,
    factor: "0.5",
    ...over,
  };
}

export function cart(over: Partial<Cart> = {}): Cart {
  return {
    kitchen_id: "k1",
    entries: [],
    editor: null,
    draft: null,
    can_edit: true,
    ...over,
  };
}

export function type(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  act(() => {
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
