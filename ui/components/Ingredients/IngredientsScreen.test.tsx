/** @vitest-environment jsdom */

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { api, useChromeHeader } = vi.hoisted(() => ({
  api: {
    fetchIngredientPlaces: vi.fn(),
    fetchPlaces: vi.fn(),
    fetchPlaceSources: vi.fn(),
    setIngredientPlace: vi.fn(),
    addPlace: vi.fn(),
    renamePlace: vi.fn(),
    deletePlace: vi.fn(),
    copyPlaces: vi.fn(),
  },
  useChromeHeader: vi.fn(),
}));
vi.mock("@/lib/places", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/places")>()),
  ...api,
}));
vi.mock("@/components/ChromeBack", () => ({ useChromeHeader }));

import { mount } from "@/components/Cart/testRoot";

import { IngredientsScreen } from "./IngredientsScreen";

const ITEMS = [
  {
    name: "flour",
    place: { kind: "default", key: "supermarket" },
    recipes: [
      { id: "r1", title: "Bread" },
      { id: "r2", title: "Pancakes" },
    ],
    last_used_at: "2026-03-01T12:00:00Z",
  },
  {
    name: "jalapeño",
    place: { kind: "default", key: "farmers_market" },
    recipes: [{ id: "r3", title: "Salsa" }],
    last_used_at: "2026-02-01T12:00:00Z",
  },
  {
    name: "miso",
    place: { kind: "custom", id: "p1", name: "Asian market" },
    recipes: [],
    last_used_at: null,
  },
];

async function settle() {
  await act(async () => {
    for (let i = 0; i < 4; i += 1) await Promise.resolve();
  });
}

function button(text: string): HTMLButtonElement {
  const found = Array.from(document.querySelectorAll("button")).filter(
    (b) => b.textContent === text,
  );
  return found[found.length - 1] as HTMLButtonElement;
}

function setValue(el: HTMLInputElement | HTMLSelectElement, value: string) {
  const proto = el instanceof HTMLSelectElement ? HTMLSelectElement : HTMLInputElement;
  const setter = Object.getOwnPropertyDescriptor(proto.prototype, "value")?.set;
  act(() => {
    setter?.call(el, value);
    el.dispatchEvent(new Event(el instanceof HTMLSelectElement ? "change" : "input", { bubbles: true }));
  });
}

describe("IngredientsScreen (spec 070 US2)", () => {
  let view: ReturnType<typeof mount>;

  beforeEach(() => {
    view = mount();
    for (const fn of Object.values(api)) fn.mockReset();
    api.fetchIngredientPlaces.mockResolvedValue({ ok: true, value: ITEMS });
    api.fetchPlaces.mockResolvedValue({
      ok: true,
      value: { defaults: [], custom: [{ id: "p1", name: "Asian market" }] },
    });
    api.fetchPlaceSources.mockResolvedValue({
      ok: true,
      value: [{ user_id: "u2", alias: "ben" }],
    });
  });
  afterEach(() => view.unmount());

  const picker = (label: string) =>
    view.container.querySelector<HTMLButtonElement>(`[role="combobox"][aria-label="${label}"]`)!;
  function pick(label: string, option: string) {
    act(() => picker(label).click());
    const found = Array.from(document.querySelectorAll<HTMLElement>('[role="option"]')).find(
      (o) => o.textContent === option,
    )!;
    act(() => found.click());
  }

  async function render(locale: "en" | "es" = "en") {
    view.render(<IngredientsScreen locale={locale} />);
    await settle();
  }

  const rows = () =>
    Array.from(view.container.querySelectorAll("tbody tr > td:first-child")).map(
      (s) => s.textContent,
    );
  const row = (name: string) =>
    Array.from(view.container.querySelectorAll("tbody tr")).find(
      (r) => r.querySelector("td")?.textContent === name,
    )!;

  it("lists each ingredient with its place, and filters ignoring accents", async () => {
    await render();
    expect(rows()).toEqual(["flour", "jalapeño", "miso"]);
    expect(picker("Where to buy miso").textContent).toContain("Asian market");
    setValue(view.container.querySelector('input[type="search"]') as HTMLInputElement, "JALAPENO");
    expect(rows()).toEqual(["jalapeño"]);
  });

  it("shows the last use and the recipes as a count with chips", async () => {
    await render();
    const flour = row("flour").querySelectorAll("td");
    expect(flour[2].textContent).toBe(new Date("2026-03-01T12:00:00Z").toLocaleDateString("en"));
    expect(flour[3].textContent).toBe("2BreadPancakes");
    const bread = flour[3].querySelector("a");
    expect(bread?.getAttribute("href")).toBe("/recipes/r1?from=%2Fingredients");
    const miso = row("miso").querySelectorAll("td");
    expect(miso[2].textContent).toBe("Never");
    expect(miso[3].textContent).toBe("0");
    // A recipe title finds the ingredients it uses.
    setValue(view.container.querySelector('input[type="search"]') as HTMLInputElement, "salsa");
    expect(rows()).toEqual(["jalapeño"]);
  });

  it("saves a place at once and puts it back when saving fails", async () => {
    api.setIngredientPlace.mockResolvedValueOnce({ ok: true, value: {} });
    await render();
    const flour = () => picker("Where to buy flour");
    pick("Where to buy flour", "Bakery");
    await settle();
    expect(api.setIngredientPlace).toHaveBeenCalledWith("flour", {
      kind: "default",
      key: "bakery",
    });
    expect(flour().textContent).toContain("Bakery");

    api.setIngredientPlace.mockResolvedValueOnce({ ok: false, status: 500, code: null });
    pick("Where to buy flour", "Butcher");
    await settle();
    expect(flour().textContent).toContain("Bakery");
    expect(view.container.querySelector('[role="alert"]')?.textContent).toBe(
      "Could not save that. Try again.",
    );
  });

  it("adds a place and shows the reason it was refused", async () => {
    api.addPlace.mockResolvedValue({ ok: false, status: 409, code: "place_name_taken" });
    await render();
    const input = Array.from(view.container.querySelectorAll("label")).find((l) =>
      l.textContent?.startsWith("New place"),
    )!.querySelector("input") as HTMLInputElement;
    setValue(input, "Supermercado");
    await act(async () => {
      button("Add place").click();
      await Promise.resolve();
    });
    expect(api.addPlace).toHaveBeenCalledWith("Supermercado");
    expect(document.body.textContent).toContain("You already have a place with that name.");
  });

  it("deletes a place only after confirming", async () => {
    api.deletePlace.mockResolvedValue({ ok: true, value: undefined });
    await render();
    act(() => button("Delete Asian market").click());
    expect(api.deletePlace).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain("Its ingredients go back to Supermarket.");
    await act(async () => {
      button("Delete").click();
      await Promise.resolve();
    });
    expect(api.deletePlace).toHaveBeenCalledWith("p1");
  });

  it("copies a member's places after confirming", async () => {
    api.copyPlaces.mockResolvedValue({ ok: true, value: { defaults: [], custom: [] } });
    await render();
    const from = Array.from(view.container.querySelectorAll("label")).find((l) =>
      l.textContent?.startsWith("Copy from"),
    )!.querySelector("select") as HTMLSelectElement;
    setValue(from, "u2");
    act(() => button("Copy").click());
    expect(document.body.textContent).toContain("Use ben's places?");
    await act(async () => {
      button("Copy").click();
      await Promise.resolve();
    });
    expect(api.copyPlaces).toHaveBeenCalledWith("u2");
  });

  it("names default places in Spanish", async () => {
    await render("es");
    act(() => picker("Dónde comprar flour").click());
    const options = Array.from(document.querySelectorAll('[role="option"]')).map(
      (o) => o.textContent,
    );
    expect(options.slice(0, 2)).toEqual(["Supermercado", "Mercado de agricultores"]);
  });
});
