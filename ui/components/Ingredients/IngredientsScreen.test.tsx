/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot } from "react-dom/client";
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
    (b) => b.textContent === text || b.getAttribute("aria-label") === text,
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

  /** The header's Location button, as the chrome would render it. */
  function locationButton(): HTMLButtonElement {
    const config = useChromeHeader.mock.calls.at(-1)?.[0] as { trailing: React.ReactElement };
    const host = document.createElement("div");
    document.body.append(host);
    act(() => createRoot(host).render(config.trailing));
    return host.querySelector("button")!;
  }

  function openPlaces() {
    const location = locationButton();
    act(() => location.click());
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
    openPlaces();
    // The first card adds a place.
    const input = view.container.querySelector<HTMLInputElement>('input[aria-label="New place"]')!;
    expect(input.placeholder).toBe("Name");
    setValue(input, "Supermercado");
    await act(async () => {
      button("Add place").click();
      await Promise.resolve();
    });
    expect(api.addPlace).toHaveBeenCalledWith("Supermercado");
    expect(document.body.textContent).toContain("You already have a place with that name.");
  });

  it("renames a place from its card: Enter saves, a refusal puts the name back", async () => {
    api.renamePlace.mockResolvedValueOnce({ ok: true, value: { id: "p1", name: "Japanese market" } });
    await render();
    openPlaces();
    const name = () =>
      view.container.querySelector<HTMLInputElement>('input[aria-label="Rename Asian market"]')!;
    setValue(name(), "Japanese market");
    act(() => {
      name().focus();
      name().dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    });
    await settle();
    expect(api.renamePlace).toHaveBeenCalledWith("p1", "Japanese market");

    api.renamePlace.mockResolvedValueOnce({ ok: false, status: 409, code: "place_name_taken" });
    act(() => name().focus());
    setValue(name(), "Supermercado");
    act(() => name().blur());
    await settle();
    expect(name().value).toBe("Asian market");
    expect(document.body.textContent).toContain("You already have a place with that name.");
  });

  it("deletes a place only after confirming", async () => {
    api.deletePlace.mockResolvedValue({ ok: true, value: undefined });
    await render();
    openPlaces();
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
    openPlaces();
    expect(picker("Copy from a member").textContent).toContain("Copy from a member");
    expect(button("Copy").disabled).toBe(true);
    pick("Copy from a member", "ben");
    act(() => button("Copy").click());
    expect(document.body.textContent).toContain("Add ben's places?");
    await act(async () => {
      button("Copy").click();
      await Promise.resolve();
    });
    expect(api.copyPlaces).toHaveBeenCalledWith("u2");
  });

  it("opens the places from the header's Location button and closes with the ✕", async () => {
    await render();
    expect(document.querySelector('[role="dialog"]')).toBeNull();
    const location = locationButton();
    expect(location.getAttribute("aria-label")).toBe("Location");
    act(() => location.click());
    const dialog = document.querySelector('[role="dialog"]')!;
    expect(dialog.querySelector("h2")?.textContent).toBe("Places");
    // One row: copy from a member, then the new place card, then the person's places.
    const cards = Array.from(dialog.querySelectorAll("ul > li"));
    expect(cards[0].querySelector('[role="combobox"]')?.textContent).toContain("Copy from a member");
    expect(cards[1].querySelector("input")?.placeholder).toBe("Name");
    expect(cards[2].querySelector("input")?.value).toBe("Asian market");
    act(() => button("Close").click());
    expect(document.querySelector('[role="dialog"]')).toBeNull();
  });

  it("lists own places A to Z, a divider, then the defaults A to Z in Spanish", async () => {
    await render("es");
    act(() => picker("Dónde comprar flour").click());
    const items = Array.from(document.querySelectorAll('[role="listbox"] > li')).map((o) =>
      o.getAttribute("role") === "separator" ? "—" : o.textContent,
    );
    expect(items).toEqual([
      "Asian market",
      "—",
      "Carnicería",
      "Farmacia o droguería",
      "Mercado de agricultores",
      "Otro",
      "Panadería",
      "Pescadería",
      "Supermercado",
    ]);
  });
});
