/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AdminDashboard } from "./AdminDashboard";

const SECTIONS: Record<string, unknown> = {
  units: {
    units: [
      {
        name: "lata",
        user_references: ["u-1", "u-2"],
        reference_count: 2,
        is_default: false,
        created_at: "2026-11-01T22:00:00Z",
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

  beforeEach(() => {
    urls = [];
    failing = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
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
      root.render(<AdminDashboard locale={locale} />);
    });
    await flush();
  }

  async function flush() {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  }

  const tab = (name: string) =>
    Array.from(container.querySelectorAll<HTMLButtonElement>('[role="tab"]')).find(
      (el) => el.textContent === name,
    )!;

  async function open(name: string) {
    await act(async () => tab(name).click());
    await flush();
  }

  it("loads only the open section, and the next when its tab is opened", async () => {
    await render();
    expect(urls).toEqual(["/api/admin/units"]);
    expect(container.textContent).toContain("lata");
    expect(container.textContent).toContain("u-1");
    expect(tab("Units").getAttribute("aria-selected")).toBe("true");

    await open("Ingredients");
    expect(urls).toEqual(["/api/admin/units", "/api/admin/ingredients"]);
    expect(container.textContent).toContain("tomate");
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
