import { afterEach, describe, expect, it, vi } from "vitest";

import {
  deleteRecipe,
  fetchKitchenRecipes,
  fetchNotebookRecipes,
  fetchRecipe,
  matchRecipeNames,
  updateRecipe,
  type RecipeDetail,
} from "./recipesClient";

const page = {
  items: [
    {
      id: "r1",
      title: "Soup",
      author_alias: "ana",
      ingredient_count: 2,
      notebook_id: "n1",
      notebook_name: "ana's Notebook",
      created_at: "2026-10-27T12:00:00Z",
    },
  ],
  page: 1,
  page_size: 12,
  total: 1,
  total_pages: 1,
};

function stub(response: Response | Error) {
  const mock = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(async () => {
    if (response instanceof Error) throw response;
    return response;
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

afterEach(() => vi.unstubAllGlobals());

describe("recipesClient", () => {
  it("reads a notebook page and sends page and filter", async () => {
    const mock = stub(new Response(JSON.stringify(page), { status: 200 }));
    const result = await fetchNotebookRecipes("n 1", 2, " soup ");
    expect(result).toEqual({ ok: true, value: page });
    expect(mock).toHaveBeenCalledWith(
      "/api/notebooks/n%201/recipes?page=2&q=+soup+",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("leaves the filter out when it is blank", async () => {
    const mock = stub(new Response(JSON.stringify(page), { status: 200 }));
    await fetchKitchenRecipes("k1", 1, "   ");
    expect(mock.mock.calls[0]?.[0]).toBe("/api/notebooks/kitchens/k1/recipes?page=1");
  });

  it("keeps the status and code of a failed read", async () => {
    stub(new Response(JSON.stringify({ code: "notebook_not_found" }), { status: 404 }));
    expect(await fetchNotebookRecipes("n1", 1, "")).toEqual({
      ok: false,
      status: 404,
      code: "notebook_not_found",
    });
  });

  it("reports a network failure as status 0", async () => {
    stub(new Error("offline"));
    expect(await fetchKitchenRecipes("k1", 1, "")).toEqual({ ok: false, status: 0, code: null });
  });

  it("rejects a malformed body", async () => {
    stub(new Response(JSON.stringify({ items: [{ id: 1 }] }), { status: 200 }));
    const result = await fetchNotebookRecipes("n1", 1, "");
    expect(result.ok).toBe(false);
  });
});

describe("one recipe (spec 027)", () => {
  const detail: RecipeDetail = {
    id: "r1",
    title: "Tomato rice",
    base_servings: 4,
    servings_estimated: false,
    author_alias: "ana",
    created_at: "2026-10-28T10:00:00Z",
    version: "2026-10-28T10:00:00.123456+00:00",
    notebook: { id: "n1", name: "ana's Notebook", kind: "personal", kitchen_id: null },
    can_write: true,
    ingredient_lines: [
      { name: "rice", vague: false, quantity: 1, unit: "cup", size: null, preparation: null, note: null },
    ],
    steps: ["Cook."],
    source: null,
  };
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
  const update = {
    version: detail.version,
    title: detail.title,
    base_servings: 4,
    servings_estimated: false,
    ingredient_lines: detail.ingredient_lines,
    steps: detail.steps,
  };

  afterEach(() => vi.unstubAllGlobals());

  it("reads a recipe", async () => {
    const mock = stub(json(detail));
    const result = await fetchRecipe("r 1");
    expect(result).toEqual({ ok: true, value: detail });
    expect(mock.mock.calls[0][0]).toBe("/api/recipes/r%201");
  });

  it("keeps the code of a missing recipe", async () => {
    stub(json({ code: "recipe_not_found" }, 404));
    expect(await fetchRecipe("r1")).toEqual({ ok: false, status: 404, code: "recipe_not_found" });
  });

  it("rejects a malformed body and a network failure", async () => {
    stub(json({ id: "r1" }));
    expect(await fetchRecipe("r1")).toMatchObject({ ok: false, status: 200 });
    stub(new Error("down"));
    expect(await fetchRecipe("r1")).toEqual({ ok: false, status: 0, code: null });
  });

  it("sends the names and returns the matches", async () => {
    const mock = stub(json({ matches: [{ name: "onions", entry: "onion" }] }));
    const result = await matchRecipeNames("r1", ["onions"]);
    expect(result).toEqual({ ok: true, value: [{ name: "onions", entry: "onion" }] });
    const [url, init] = mock.mock.calls[0];
    expect(url).toBe("/api/recipes/r1/name-matches");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify({ names: ["onions"] }));
  });

  it("saves an edit with its version", async () => {
    const mock = stub(json(detail));
    const result = await updateRecipe("r1", update);
    expect(result).toEqual({ ok: true, value: detail });
    expect(mock.mock.calls[0][1]?.method).toBe("PUT");
    expect(JSON.parse(String(mock.mock.calls[0][1]?.body)).version).toBe(detail.version);
  });

  it("keeps a changed-since-opened answer", async () => {
    stub(json({ code: "recipe_changed" }, 409));
    expect(await updateRecipe("r1", update)).toMatchObject({
      ok: false,
      status: 409,
      code: "recipe_changed",
    });
  });

  it("keeps the named problems of a refused edit", async () => {
    stub(
      json(
        {
          code: "ingredient_line_problem",
          missing: ["title"],
          line_problems: [{ name: "rice", kind: "unit_missing" }, "junk"],
        },
        422,
      ),
    );
    expect(await updateRecipe("r1", update)).toEqual({
      ok: false,
      status: 422,
      code: "ingredient_line_problem",
      missing: ["title"],
      lineProblems: [{ name: "rice", kind: "unit_missing" }],
    });
  });

  it("deletes with an empty 204 and reports a 404", async () => {
    const mock = stub(new Response(null, { status: 204 }));
    expect(await deleteRecipe("r1")).toEqual({ ok: true, value: true });
    expect(mock.mock.calls[0][1]?.method).toBe("DELETE");
    stub(json({ code: "recipe_not_found" }, 404));
    expect(await deleteRecipe("r1")).toMatchObject({ ok: false, status: 404 });
  });

  it("reports a network failure for a change as status 0", async () => {
    stub(new Error("down"));
    expect(await updateRecipe("r1", update)).toEqual({ ok: false, status: 0, code: null });
  });
});
