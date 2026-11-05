/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ChromeBackProvider,
  useChromeHeaderState,
} from "@/components/ChromeBack";
import { MIN_LOADING_MS } from "@/lib/minimumLoading";

import { AdminDashboard } from "./AdminDashboard";

vi.mock("next/navigation", () => ({ usePathname: () => "/admin" }));

/** The part of AppShell's header that holds the tabs. */
function Tabs() {
  return <>{useChromeHeaderState().titleAside}</>;
}

function Screen({ locale }: { locale: "en" | "es" }) {
  return (
    <ChromeBackProvider>
      <Tabs />
      <AdminDashboard locale={locale} />
    </ChromeBackProvider>
  );
}

const SECTIONS: Record<string, unknown> = {
  units: {
    units: [
      {
        name: "lata",
        user_references: ["u-1", "u-2"],
        user_aliases: ["ana", null],
        reference_count: 2,
        is_default: false,
        created_at: "2026-11-01T22:00:00Z",
      },
      {
        name: "cup",
        user_references: [],
        user_aliases: [],
        reference_count: 9,
        is_default: true,
        created_at: "2026-10-01T22:00:00Z",
      },
    ],
  },
  ingredients: { ingredients: [{ name: "tomate", recipes: 4, people: 2 }] },
  recipes: {
    recipes: [
      {
        id: "r1",
        title: "Sopa",
        cart_adds: 5,
        notebook_name: "Cuaderno de Ana",
        notebook_kind: "kitchen",
        people_with_access: 3,
        people_aliases: ["ana", null, "ben"],
      },
      {
        id: "r2",
        title: "Pan",
        cart_adds: 1,
        notebook_name: "Cuaderno de Ben",
        notebook_kind: "personal",
        people_with_access: 1,
        people_aliases: ["ben"],
      },
    ],
  },
  users: {
    users: [
      {
        id: "u-1",
        alias: null,
        open_sessions: 2,
        newest_session_at: "2026-11-01T20:00:00Z",
        recipes_authored: 7,
        latest_recipe_at: null,
        carts_created: 1,
        carts_edited: 1,
        carts_closed: 1,
        latest_cart_action_at: null,
      },
    ],
  },
};

describe("AdminDashboard", () => {
  let container: HTMLDivElement;
  let root: Root;
  let urls: string[];
  let failing: boolean;
  let deletes: string[];
  let deleteStatus: number;

  beforeEach(() => {
    urls = [];
    deletes = [];
    deleteStatus = 204;
    failing = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method === "DELETE") {
          deletes.push(url);
          return new Response(null, { status: deleteStatus });
        }
        urls.push(url);
        if (failing) return new Response("{}", { status: 500 });
        const section = url.split("/").pop() as string;
        return new Response(JSON.stringify(SECTIONS[section]));
      }),
    );
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  async function render(locale: "en" | "es" = "en") {
    await act(async () => {
      root.render(<Screen locale={locale} />);
    });
    await flush();
  }

  async function flush() {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, MIN_LOADING_MS + 20));
    });
  }

  const tab = (name: string) =>
    Array.from(
      container.querySelectorAll<HTMLButtonElement>('[role="tab"]'),
    ).find((el) => el.textContent === name)!;

  async function open(name: string) {
    await act(async () => tab(name).click());
    await flush();
  }

  const button = (label: string) =>
    container.querySelector<HTMLButtonElement>(
      `button[aria-label="${label}"]`,
    )!;

  const dialog = () => document.querySelector<HTMLElement>('[role="dialog"]');

  const confirmButton = () =>
    Array.from(dialog()!.querySelectorAll<HTMLButtonElement>("button")).find(
      (el) => el.textContent === "Delete",
    )!;

  it("loads only the open section, and the next when its tab is opened", async () => {
    await render();
    expect(urls).toEqual(["/api/admin/units"]);
    expect(container.textContent).toContain("lata");
    expect(container.textContent).toContain("ana");
    expect(tab("Units").getAttribute("aria-selected")).toBe("true");

    await open("Ingredients");
    expect(urls).toEqual(["/api/admin/units", "/api/admin/ingredients"]);
    expect(container.textContent).toContain("tomate");
  });

  it("marks a default unit with a check and any other with an x, named for screen readers", async () => {
    await render();
    const marks = Array.from(container.querySelectorAll('td [role="img"]'));
    expect(marks.map((mark) => mark.getAttribute("aria-label"))).toEqual([
      "No",
      "Yes",
    ]);
    expect(
      marks.every(
        (mark) => mark.querySelector("svg") && mark.textContent === "",
      ),
    ).toBe(true);
    expect(marks[0].querySelector("path")?.getAttribute("d")).not.toBe(
      marks[1].querySelector("path")?.getAttribute("d"),
    );
  });

  it("shows the cauldron for the first load of a section, even when the data is there", async () => {
    await act(async () => {
      root.render(<Screen locale="en" />);
    });
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });
    expect(urls).toEqual(["/api/admin/units"]);
    expect(container.querySelector("table")).toBeNull();
    await flush();
    expect(container.querySelector("table")).not.toBeNull();
  });

  it("shows a section already loaded at once, with no cauldron", async () => {
    await render();
    await open("Recipes");
    await act(async () => tab("Units").click());
    expect(container.textContent).toContain("lata");
    expect(container.querySelector("table")).not.toBeNull();
  });

  it("asks once when a tab is left and reopened while it loads", async () => {
    await render();
    await act(async () => tab("Recipes").click());
    await act(async () => tab("Users").click());
    await act(async () => tab("Recipes").click());
    await flush();
    expect(urls.filter((url) => url.endsWith("/recipes"))).toHaveLength(1);
  });

  it("does not load a section twice", async () => {
    await render();
    await open("Recipes");
    await open("Units");
    expect(urls).toEqual(["/api/admin/units", "/api/admin/recipes"]);
  });

  it("shows the recipe figures and the kind in the reader's language", async () => {
    await render("es");
    await open("Recetas");
    expect(container.textContent).toContain("Sopa");
    expect(container.textContent).toContain("Cocina");
  });

  it("shows a dash for a missing date and a label for a missing alias", async () => {
    await render();
    await open("Users");
    expect(container.textContent).toContain("No alias");
    expect(container.textContent).toContain("—");
  });

  it("shows the count of people with access, then their aliases as chips", async () => {
    await render();
    await open("Recipes");
    const cell = container.querySelector("tbody tr td:nth-child(5)")!;
    expect(cell.querySelector("span")?.textContent).toBe("3");
    const chips = Array.from(cell.querySelectorAll("span.inline-flex")).map(
      (el) => el.textContent,
    );
    expect(chips).toEqual(["ana", "No alias", "ben"]);
    expect(cell.querySelector(".overflow-x-auto")).not.toBeNull();
  });

  it("deletes a recipe after confirming, and drops its row", async () => {
    await render();
    await open("Recipes");
    await act(async () => button("Delete recipe Sopa").click());
    expect(dialog()).not.toBeNull();
    expect(deletes).toEqual([]);

    await act(async () => confirmButton().click());
    await flush();
    expect(deletes).toEqual(["/api/admin/recipes/r1"]);
    expect(dialog()).toBeNull();
    expect(container.textContent).not.toContain("Sopa");
    expect(container.textContent).toContain("Pan");
  });

  it("keeps the recipe and says so when the delete fails", async () => {
    deleteStatus = 500;
    await render();
    await open("Recipes");
    await act(async () => button("Delete recipe Sopa").click());
    await act(async () => confirmButton().click());
    await flush();
    expect(dialog()?.querySelector('[role="alert"]')?.textContent).toContain(
      "couldn't delete",
    );
    expect(container.textContent).toContain("Sopa");
  });

  it("does not delete when the confirmation is cancelled", async () => {
    await render();
    await open("Recipes");
    await act(async () => button("Delete recipe Sopa").click());
    const cancel = Array.from(dialog()!.querySelectorAll("button")).find(
      (el) => el.textContent === "Cancel",
    )!;
    await act(async () => cancel.click());
    expect(dialog()).toBeNull();
    expect(deletes).toEqual([]);
  });

  it("shows the units' count of people, then their aliases as chips", async () => {
    await render();
    const cell = container.querySelector("tbody tr td:nth-child(5)")!;
    expect(cell.querySelector("span")?.textContent).toBe("2");
    const chips = Array.from(cell.querySelectorAll("span.inline-flex")).map(
      (el) => el.textContent,
    );
    expect(chips).toEqual(["ana", "No alias"]);
  });

  const firstCells = () =>
    Array.from(container.querySelectorAll("tbody tr td:first-child")).map(
      (td) => td.textContent,
    );
  const search = () => container.querySelector<HTMLInputElement>("input");
  function type(text: string) {
    const setter = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    )!.set!;
    act(() => {
      setter.call(search()!, text);
      search()!.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }

  describe("sort and search (spec 066)", () => {
    beforeEach(() => {
      (SECTIONS.units as { units: unknown[] }).units.push({
        name: "taza",
        user_references: [],
        user_aliases: [],
        reference_count: 2,
        is_default: false,
        created_at: null,
      });
      (SECTIONS.ingredients as { ingredients: unknown[] }).ingredients.push({
        name: "ajo",
        recipes: 9,
        people: 1,
      });
      (SECTIONS.users as { users: unknown[] }).users.push({
        id: "u-2",
        alias: "ben",
        open_sessions: 10,
        newest_session_at: null,
        recipes_authored: 0,
        latest_recipe_at: "2026-10-01T00:00:00Z",
        carts_created: 0,
        carts_edited: 0,
        carts_closed: 0,
        latest_cart_action_at: null,
      });
    });

    afterEach(() => {
      (SECTIONS.units as { units: unknown[] }).units.pop();
      (SECTIONS.ingredients as { ingredients: unknown[] }).ingredients.pop();
      (SECTIONS.users as { users: unknown[] }).users.pop();
    });

    it("sorts each tab by a numeric heading, asc then desc, with no request", async () => {
      await render();
      const numeric = async (col: number) => {
        await act(async () =>
          container.querySelectorAll<HTMLButtonElement>("th button")[col].click(),
        );
        const asc = firstCells();
        await act(async () =>
          container.querySelectorAll<HTMLButtonElement>("th button")[col].click(),
        );
        return [asc, firstCells()];
      };
      expect(await numeric(1)).toEqual([
        ["lata", "taza", "cup"],
        ["cup", "lata", "taza"],
      ]);
      await open("Ingredients");
      expect(await numeric(1)).toEqual([
        ["tomate", "ajo"],
        ["ajo", "tomate"],
      ]);
      await open("Recipes");
      expect(await numeric(1)).toEqual([
        ["Pan", "Sopa"],
        ["Sopa", "Pan"],
      ]);
      await open("Users");
      expect(await numeric(1)).toEqual([
        ["No alias", "ben"],
        ["ben", "No alias"],
      ]);
      expect(urls).toHaveLength(4);
    });

    it("sorts Units by Count then Name", async () => {
      await render();
      const buttons = () =>
        container.querySelectorAll<HTMLButtonElement>("th button");
      await act(async () => buttons()[1].click());
      await act(async () => buttons()[0].click());
      await act(async () => buttons()[0].click());
      expect(firstCells()).toEqual(["taza", "lata", "cup"]);
    });

    it("restores the default order and an empty search when the tab changes", async () => {
      await render();
      await act(async () =>
        container.querySelectorAll<HTMLButtonElement>("th button")[1].click(),
      );
      type("a");
      await open("Ingredients");
      await act(async () => tab("Units").click());
      expect(firstCells()).toEqual(["lata", "cup", "taza"]);
      expect(search()!.value).toBe("");
    });

    it("filters Recipes as the admin types, and Users has no search bar", async () => {
      await render();
      await open("Recipes");
      type("sop");
      expect(firstCells()).toEqual(["Sopa"]);
      type("BEN");
      expect(firstCells()).toEqual(["Sopa", "Pan"]);
      await open("Users");
      expect(search()).toBeNull();
    });
  });

  it("says so when a section fails, and tries again", async () => {
    failing = true;
    await render();
    expect(container.textContent).toContain("couldn't load");
    failing = false;
    const retry = Array.from(container.querySelectorAll("button")).find(
      (el) => el.textContent === "Try again",
    )!;
    await act(async () => retry.click());
    await flush();
    expect(container.textContent).toContain("lata");
  });
});
