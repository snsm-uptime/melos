/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RecipeFromNotebookSheet } from "./RecipeFromNotebookSheet";

const prefs = vi.hoisted(() => ({
  value: null as { locale: "en" | "es" } | null,
}));
vi.mock("@/components/PreferencesProvider", () => ({
  useOptionalPreferences: () => prefs.value,
}));

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function notebook(
  id: string,
  name: string,
  kind: "personal" | "kitchen",
  count: number,
  isDefault = false,
) {
  return {
    id,
    name,
    kind,
    owner_alias: "ana",
    access: kind === "personal" ? "owner" : "kitchen_member",
    is_default: isDefault,
    recipe_count: count,
    kitchen_id: kind === "kitchen" ? "k1" : null,
    kitchen_is_archived: kind === "kitchen" ? false : null,
    origin_notebook_name: null,
    is_snapshot: false,
    is_own_capture_notebook: false,
  };
}

function page(titles: string[]) {
  return {
    items: titles.map((title, index) => ({
      id: `r${index + 1}`,
      title,
      author_alias: "ana",
      ingredient_count: 3,
      notebook_id: "p1",
      notebook_name: "ana's Notebook",
      created_at: "2026-11-04T00:00:00Z",
    })),
    page: 1,
    page_size: 20,
    total: titles.length,
    total_pages: 1,
  };
}

type Copy = { status: number; body: unknown };

let container: HTMLDivElement;
let root: Root;
let notebooks: unknown[];
let copies: Copy[];
let posted: {
  url: string;
  body: { source_recipe_id: string; on_repeat: string };
}[];
let recipeQueries: string[];

function fetchMock(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const url = String(input);
  if (url === "/api/notebooks")
    return Promise.resolve(json(200, { notebooks }));
  if (
    url.startsWith("/api/notebooks/p1/recipes") ||
    url.startsWith("/api/notebooks/p2/recipes")
  ) {
    recipeQueries.push(url);
    const q = new URL(url, "http://x").searchParams.get("q") ?? "";
    const all = url.includes("/p2/")
      ? ["Carrot cake"]
      : ["Lentil soup", "Pea soup"];
    const titles = all.filter((title) =>
      title.toLowerCase().includes(q.toLowerCase()),
    );
    return Promise.resolve(json(200, page(titles)));
  }
  if (url.endsWith("/recipe-copies")) {
    posted.push({ url, body: JSON.parse(String(init?.body)) });
    const next = copies.shift() ?? { status: 500, body: {} };
    return Promise.resolve(json(next.status, next.body));
  }
  return Promise.resolve(json(404, {}));
}

async function flush() {
  await act(async () => {
    for (let i = 0; i < 20; i += 1) await Promise.resolve();
  });
}

async function render(
  props: Partial<Parameters<typeof RecipeFromNotebookSheet>[0]> = {},
) {
  const onDone = props.onDone ?? vi.fn();
  await act(async () => {
    root.render(
      <RecipeFromNotebookSheet
        open
        onClose={vi.fn()}
        kitchenId="k1"
        {...props}
        onDone={onDone}
      />,
    );
  });
  await flush();
  return onDone;
}

function byText(text: string): HTMLButtonElement | null {
  return (
    (Array.from(document.querySelectorAll("button")).find(
      (el) => el.textContent?.trim() === text,
    ) as HTMLButtonElement | undefined) ?? null
  );
}

function byLabel(label: string): HTMLButtonElement | null {
  return document.querySelector(
    `button[aria-label='${label}']`,
  ) as HTMLButtonElement | null;
}

/** The save button at the bottom of the pop-up. */
function saveButton(): HTMLButtonElement {
  return byText("Save")!;
}

async function click(text: string) {
  await act(async () => byText(text)!.click());
  await flush();
}

/** Opens a searchable select by its label and chooses the option with this text. */
async function choose(label: string, option: string) {
  await act(async () => byLabel(label)!.click());
  await act(async () => {
    const match = Array.from(document.querySelectorAll("[role='option']")).find(
      (el) => el.textContent?.trim() === option,
    ) as HTMLElement | undefined;
    match!.click();
  });
  await flush();
}

const ORIGINAL = "Original notebook";
const RECIPES = "Search recipes";

const copied = {
  recipe_id: "c1",
  notebook_id: "kn1",
  notebook_name: "ana's (Home) Notebook",
  overwritten: false,
};

beforeEach(() => {
  prefs.value = null;
  notebooks = [
    notebook("p1", "ana's Notebook", "personal", 2, true),
    notebook("p2", "Family list", "personal", 1),
    notebook("kn", "Home notebook", "kitchen", 4),
  ];
  copies = [];
  posted = [];
  recipeQueries = [];
  vi.stubGlobal("fetch", vi.fn(fetchMock));
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

describe("RecipeFromNotebookSheet (spec 069)", () => {
  it("quick add: the recipe select stays disabled until an original notebook is chosen", async () => {
    await render({ kitchenId: "k1" });
    expect(byLabel(ORIGINAL)!.textContent).toContain("Choose a notebook");
    expect(byLabel(RECIPES)!.disabled).toBe(true);
    expect(recipeQueries).toEqual([]);

    await choose(ORIGINAL, "Family list");
    expect(recipeQueries[0]).toContain("/api/notebooks/p2/recipes");
    expect(byLabel(RECIPES)!.disabled).toBe(false);
  });

  it("quick add: the original notebook lists every readable notebook, kitchens included", async () => {
    await render({ kitchenId: "k1" });
    await act(async () => byLabel(ORIGINAL)!.click());
    const names = Array.from(document.querySelectorAll("[role='option']")).map(
      (el) => el.textContent,
    );
    expect(names).toEqual(["ana's Notebook", "Family list", "Home notebook"]);
  });

  it("on a personal notebook page the original notebook is fixed and its recipes load at once", async () => {
    await render({ kitchenId: "k1", sourceNotebookId: "p1" });
    expect(byLabel(ORIGINAL)).toBeNull();
    expect(document.body.textContent).toContain("ana's Notebook");
    expect(recipeQueries[0]).toContain("/api/notebooks/p1/recipes");
    expect(byLabel(RECIPES)!.disabled).toBe(false);
  });

  it("says so and offers no recipe select when the personal notebooks have no recipes", async () => {
    notebooks = [notebook("p1", "ana's Notebook", "personal", 0, true)];
    await render();
    expect(document.body.textContent).toContain(
      "Your personal notebooks have no recipes yet.",
    );
    expect(byLabel(RECIPES)).toBeNull();
  });

  it("the save icon stays disabled until a recipe is chosen, then copies it into the open kitchen", async () => {
    copies = [{ status: 201, body: copied }];
    const onDone = await render({ kitchenId: "k1", sourceNotebookId: "p1" });
    expect(saveButton().disabled).toBe(true);

    await choose(RECIPES, "Lentil soup");
    expect(saveButton().disabled).toBe(false);
    await act(async () => saveButton().click());
    await flush();

    expect(posted).toEqual([
      {
        url: "/api/notebooks/kitchens/k1/recipe-copies",
        body: { source_recipe_id: "r1", on_repeat: "ask" },
      },
    ]);
    expect(onDone).toHaveBeenCalledWith(copied, "k1");
  });

  it("the recipe select lists every recipe of the notebook, and searching narrows it", async () => {
    await render({ kitchenId: "k1", sourceNotebookId: "p1" });
    await act(async () => byLabel(RECIPES)!.click());
    const names = () =>
      Array.from(document.querySelectorAll("[role='option']")).map(
        (el) => el.textContent,
      );
    expect(names()).toEqual(["Lentil soup", "Pea soup"]);
    const search = document.querySelector("input") as HTMLInputElement;
    await act(async () => {
      Object.getOwnPropertyDescriptor(
        HTMLInputElement.prototype,
        "value",
      )!.set!.call(search, "pea");
      search.dispatchEvent(new Event("input", { bubbles: true }));
    });
    expect(names()).toEqual(["Pea soup"]);
  });

  it("the target kitchen is shown, not chosen, when the add is inside a kitchen", async () => {
    await render({
      kitchenId: "k1",
      kitchenName: "Home",
      sourceNotebookId: "p1",
    });
    expect(byLabel("Target kitchen")).toBeNull();
    expect(document.body.textContent).toContain("Home");
  });

  it.each([
    ["Add another copy", "add"],
    ["Overwrite", "overwrite"],
  ])("on a repeat, %s posts on_repeat=%s", async (choice, onRepeat) => {
    copies = [
      {
        status: 409,
        body: {
          code: "recipe_already_in_kitchen",
          existing_recipe_id: "c0",
          notebook_name: "ana's (Home) Notebook",
        },
      },
      {
        status: onRepeat === "add" ? 201 : 200,
        body: { ...copied, overwritten: onRepeat === "overwrite" },
      },
    ];
    const onDone = await render({ kitchenId: "k1", sourceNotebookId: "p1" });
    await choose(RECIPES, "Lentil soup");
    await act(async () => saveButton().click());
    await flush();

    expect(document.body.textContent).toContain("Already in this kitchen");
    expect(document.body.textContent).toContain("ana's (Home) Notebook");
    await click(choice);

    expect(posted.map((p) => p.body.on_repeat)).toEqual(["ask", onRepeat]);
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it("on a repeat, Cancel posts nothing more", async () => {
    copies = [
      {
        status: 409,
        body: { code: "recipe_already_in_kitchen", notebook_name: "N" },
      },
    ];
    const onDone = await render({ kitchenId: "k1", sourceNotebookId: "p1" });
    await choose(RECIPES, "Lentil soup");
    await act(async () => saveButton().click());
    await flush();
    await click("Cancel");

    expect(posted).toHaveLength(1);
    expect(onDone).not.toHaveBeenCalled();
    expect(saveButton()).not.toBeNull();
  });

  it("explains a recipe deleted while the select was open", async () => {
    copies = [{ status: 404, body: { code: "recipe_not_found" } }];
    await render({ kitchenId: "k1", sourceNotebookId: "p1" });
    await choose(RECIPES, "Lentil soup");
    await act(async () => saveButton().click());
    await flush();
    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "That recipe is no longer available. Pick another one.",
    );
  });

  it("outside a kitchen asks which kitchen when there are two", async () => {
    copies = [{ status: 201, body: copied }];
    const onDone = await render({
      kitchenId: null,
      sourceNotebookId: "p1",
      kitchens: [
        { id: "k1", name: "Home" },
        { id: "k2", name: "Cabin" },
      ],
    });
    expect(byLabel("Target kitchen")).not.toBeNull();
    await choose(RECIPES, "Lentil soup");
    expect(saveButton().disabled).toBe(true);

    await choose("Target kitchen", "Cabin");
    await act(async () => saveButton().click());
    await flush();

    expect(posted[0].url).toBe("/api/notebooks/kitchens/k2/recipe-copies");
    expect(onDone).toHaveBeenCalledWith(copied, "k2");
  });

  it("outside a kitchen shows the only kitchen without a choice", async () => {
    await render({
      kitchenId: null,
      sourceNotebookId: "p1",
      kitchens: [{ id: "k1", name: "Home" }],
    });
    expect(byLabel("Target kitchen")).toBeNull();
    await choose(RECIPES, "Lentil soup");
    expect(saveButton().disabled).toBe(false);
  });

  it("reads in Spanish", async () => {
    prefs.value = { locale: "es" };
    await render({ kitchenId: "k1", sourceNotebookId: "p1" });
    expect(document.body.textContent).toContain("Receta de otro cuaderno");
    expect(document.body.textContent).toContain("Cuaderno original");
    expect(document.body.textContent).toContain("Guardar");
  });
});
