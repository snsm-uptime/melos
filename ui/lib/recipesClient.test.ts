import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchKitchenRecipes, fetchNotebookRecipes } from "./recipesClient";

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
