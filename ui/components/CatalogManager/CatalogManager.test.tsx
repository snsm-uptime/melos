/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NotebookCatalog } from "@/lib/catalogClient";

import { CatalogManager } from "./CatalogManager";

const CATALOG: NotebookCatalog = {
  notebook_id: "nb-1",
  can_write: true,
  ingredients: [
    { name: "cebolla", language: null, recipe_count: 1, variants: [], spellings: [] },
    {
      name: "garlic",
      language: "en",
      recipe_count: 2,
      variants: [{ name: "ajo", language: "es" }],
      spellings: ["garlic clove"],
    },
    { name: "onion", language: "en", recipe_count: 3, variants: [], spellings: [] },
    { name: "saffron", language: null, recipe_count: 0, variants: [], spellings: [] },
  ],
};

type Reply = { status: number; body?: unknown };
type Route = (init: RequestInit | undefined) => Reply;

/** Fetch answers by "METHOD path"; every call is kept for the assertions. */
function stubApi(routes: Record<string, Route>) {
  const calls: { key: string; body: unknown }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const key = `${init?.method ?? "GET"} ${url}`;
      calls.push({ key, body: init?.body ? JSON.parse(String(init.body)) : undefined });
      const route = routes[key];
      const reply = route ? route(init) : { status: 404, body: { code: "not_found" } };
      if (reply.status === 204) return new Response(null, { status: 204 });
      return new Response(JSON.stringify(reply.body ?? {}), { status: reply.status });
    }),
  );
  return calls;
}

const CATALOG_URL = "GET /api/notebooks/nb-1/catalog";
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("CatalogManager", () => {
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
    document.body.innerHTML = "";
  });

  async function render() {
    await act(async () => {
      root.render(<CatalogManager locale="en" notebookId="nb-1" />);
    });
    await act(async () => {
      await flush();
    });
  }

  const button = (label: string) =>
    document.querySelector<HTMLButtonElement>(`button[aria-label="${label}"]`);
  const dialog = () => document.querySelector<HTMLElement>('[role="dialog"]');
  const status = () => document.querySelector('[role="status"]')?.textContent ?? "";

  async function click(element: HTMLElement | null) {
    expect(element).not.toBeNull();
    await act(async () => {
      element!.click();
      await flush();
    });
  }

  async function chooseKept(name: string) {
    const trigger = dialog()!.querySelector<HTMLButtonElement>('[role="combobox"]')!;
    act(() => trigger.click());
    const option = Array.from(document.querySelectorAll<HTMLElement>('[role="option"]')).find(
      (o) => o.textContent === name,
    )!;
    await click(option);
  }

  function dialogButton(text: string) {
    return Array.from(dialog()!.querySelectorAll<HTMLButtonElement>("button")).find(
      (b) => b.textContent === text,
    )!;
  }

  it("lists each name with its language and other names", async () => {
    stubApi({ [CATALOG_URL]: () => ({ status: 200, body: CATALOG }) });
    await render();
    const text = document.body.textContent ?? "";
    expect(text).toContain("ajo (ES)");
    expect(text).toContain("garlic clove (spelling)");
    expect(button("Rename onion")).not.toBeNull();
    expect(button("Split ajo out")).not.toBeNull();
  });

  it("shows no action on a notebook the person can only read", async () => {
    stubApi({ [CATALOG_URL]: () => ({ status: 200, body: { ...CATALOG, can_write: false } }) });
    await render();
    expect(document.body.textContent).toContain("You can read this catalog but not change it.");
    expect(button("Rename onion")).toBeNull();
    expect(button("Merge onion")).toBeNull();
    expect(button("Split ajo out")).toBeNull();
    expect(document.body.textContent).not.toContain("Suggest pairs");
  });

  it("previews a merge, lets the person fix a language, and announces a skipped notebook", async () => {
    const calls = stubApi({
      [CATALOG_URL]: () => ({ status: 200, body: CATALOG }),
      "POST /api/catalog/merge-preview": () => ({
        status: 200,
        body: {
          merged: "cebolla",
          kept: "onion",
          merged_language: "en",
          kept_language: "en",
          notebooks: [
            { notebook_id: "nb-1", name: "Home", recipe_count: 1 },
            { notebook_id: "nb-2", name: "Ana's Notebook", recipe_count: 2 },
          ],
        },
      }),
      "POST /api/catalog/merge": () => ({
        status: 200,
        body: {
          merged: [{ notebook_id: "nb-1", recipes_changed: 1 }],
          skipped: [{ notebook_id: "nb-2", reason: "name_changed" }],
        },
      }),
    });
    await render();

    await click(button("Merge cebolla"));
    await chooseKept("onion");

    expect(dialog()!.textContent).toContain("Home: 1 recipe uses it");
    expect(dialog()!.textContent).toContain("Ana's Notebook: 2 recipes use it");
    const spanish = Array.from(
      dialog()!.querySelectorAll<HTMLInputElement>('fieldset input[type="radio"]'),
    )[1];
    await click(spanish);
    await click(dialogButton("Merge"));

    const merge = calls.find((c) => c.key === "POST /api/catalog/merge")!;
    expect(merge.body).toEqual({
      merged: "cebolla",
      kept: "onion",
      merged_language: "es",
      kept_language: "en",
      notebook_ids: ["nb-1", "nb-2"],
    });
    expect(status()).toContain("Merged “cebolla” into “onion” in 1 notebook.");
    expect(status()).toContain("1 notebook was skipped");
    expect(dialog()).toBeNull();
  });

  it("offers a merge when a rename hits an existing name", async () => {
    stubApi({
      [CATALOG_URL]: () => ({ status: 200, body: CATALOG }),
      "PATCH /api/notebooks/nb-1/catalog/cebolla": () => ({
        status: 409,
        body: { code: "name_exists", existing: "onion" },
      }),
      "POST /api/catalog/merge-preview": () => ({
        status: 200,
        body: {
          merged: "cebolla",
          kept: "onion",
          merged_language: "es",
          kept_language: "en",
          notebooks: [{ notebook_id: "nb-1", name: "Home", recipe_count: 1 }],
        },
      }),
    });
    await render();
    await click(button("Rename cebolla"));
    const field = dialog()!.querySelector<HTMLInputElement>("input:not([type])")!;
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
      setter.call(field, "onions");
      field.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await click(dialogButton("Save"));
    expect(dialog()!.textContent).toContain("“onion” is already in this catalog.");

    await click(dialogButton("Merge into onion"));
    expect(dialog()!.textContent).toContain("Merge cebolla");
    expect(dialog()!.textContent).toContain("Home: 1 recipe uses it");
  });

  it("refuses a rename to the ingredient's own other name without a merge offer", async () => {
    stubApi({
      [CATALOG_URL]: () => ({ status: 200, body: CATALOG }),
      "PATCH /api/notebooks/nb-1/catalog/garlic": () => ({
        status: 409,
        body: { code: "name_is_own_other_name" },
      }),
    });
    await render();
    await click(button("Rename garlic"));
    const field = dialog()!.querySelector<HTMLInputElement>("input:not([type])")!;
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
      setter.call(field, "ajo");
      field.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await click(dialogButton("Save"));
    expect(dialog()!.textContent).toContain("“ajo” is already another name of “garlic”.");
    expect(dialogButton("Merge into garlic")).toBeUndefined();
  });

  it("refuses to delete a used name with its count and offers a merge", async () => {
    stubApi({ [CATALOG_URL]: () => ({ status: 200, body: CATALOG }) });
    await render();
    await click(button("Delete onion"));
    expect(dialog()!.textContent).toContain("3 recipes use this name");
    expect(dialogButton("Delete")).toBeUndefined();
    await click(dialogButton("Merge instead"));
    expect(dialog()!.textContent).toContain("Merge onion");
  });

  it("deletes an unused name and announces it", async () => {
    const calls = stubApi({
      [CATALOG_URL]: () => ({ status: 200, body: CATALOG }),
      "DELETE /api/notebooks/nb-1/catalog/saffron": () => ({ status: 204 }),
    });
    await render();
    await click(button("Delete saffron"));
    await click(dialogButton("Delete"));
    expect(calls.some((c) => c.key === "DELETE /api/notebooks/nb-1/catalog/saffron")).toBe(true);
    expect(status()).toBe("Deleted “saffron”.");
  });

  it("splits an other name out after a confirmation", async () => {
    const calls = stubApi({
      [CATALOG_URL]: () => ({ status: 200, body: CATALOG }),
      "POST /api/notebooks/nb-1/catalog/garlic/split": () => ({
        status: 200,
        body: { kept: CATALOG.ingredients[1], split: CATALOG.ingredients[1], recipes_changed: 1 },
      }),
    });
    await render();
    await click(button("Split ajo out"));
    expect(dialog()!.textContent).toContain("Every recipe keeps the words it shows now.");
    await click(dialogButton("Split"));
    const split = calls.find((c) => c.key.endsWith("/garlic/split"))!;
    expect(split.body).toEqual({ other_name: "ajo" });
    expect(status()).toBe("“ajo” is its own ingredient again.");
  });

  it("accepts a suggested pair into the merge and dismisses another", async () => {
    const calls = stubApi({
      [CATALOG_URL]: () => ({ status: 200, body: CATALOG }),
      "POST /api/notebooks/nb-1/catalog/pair-suggestions": () => ({
        status: 200,
        body: {
          pairs: [
            { en: "onion", es: "cebolla" },
            { en: "saffron", es: "cebolla" },
          ],
        },
      }),
      "POST /api/notebooks/nb-1/catalog/pair-dismissals": () => ({ status: 204 }),
      "POST /api/catalog/merge-preview": () => ({
        status: 200,
        body: {
          merged: "cebolla",
          kept: "onion",
          merged_language: "es",
          kept_language: "en",
          notebooks: [{ notebook_id: "nb-1", name: "Home", recipe_count: 1 }],
        },
      }),
    });
    await render();
    await click(
      Array.from(document.querySelectorAll<HTMLButtonElement>("button")).find(
        (b) => b.textContent === "Suggest pairs",
      )!,
    );
    await click(button("Not the same: saffron and cebolla"));
    expect(status()).toBe("That pair won't be suggested again.");
    expect(calls.find((c) => c.key.endsWith("/pair-dismissals"))!.body).toEqual({
      en: "saffron",
      es: "cebolla",
    });

    await click(button("Merge onion and cebolla"));
    expect(dialog()!.textContent).toContain("Merge cebolla");
    expect(dialog()!.textContent).toContain("Home: 1 recipe uses it");
  });

  it("says when no suggestion could be made", async () => {
    stubApi({
      [CATALOG_URL]: () => ({ status: 200, body: CATALOG }),
      "POST /api/notebooks/nb-1/catalog/pair-suggestions": () => ({
        status: 503,
        body: { code: "ai_unavailable" },
      }),
    });
    await render();
    await click(
      Array.from(document.querySelectorAll<HTMLButtonElement>("button")).find(
        (b) => b.textContent === "Suggest pairs",
      )!,
    );
    expect(document.querySelector('[role="alert"]')?.textContent).toContain(
      "No suggestions could be made right now.",
    );
  });

  it("closes a dialog with Escape and keeps the actions focusable", async () => {
    stubApi({ [CATALOG_URL]: () => ({ status: 200, body: CATALOG }) });
    await render();
    const merge = button("Merge onion")!;
    merge.focus();
    expect(document.activeElement).toBe(merge);
    await click(merge);
    expect(dialog()).not.toBeNull();
    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      await flush();
    });
    expect(dialog()).toBeNull();
  });
});
