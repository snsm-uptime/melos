import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchShoppingList, type ShoppingList } from "./shoppingListClient";

const fetchMock = vi.fn();

const LIST: ShoppingList = {
  is_empty: false,
  lines: [
    {
      name: "flour",
      kind: "volume",
      size: null,
      amounts: [{ quantity: "1", unit: "cup" }],
      recipes: [{ recipe_id: "r1", title: "Bread" }],
    },
  ],
  your_call: [],
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

describe("fetchShoppingList", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("GETs the BFF path with same-origin credentials and returns the list", async () => {
    fetchMock.mockResolvedValue(json(LIST));

    const result = await fetchShoppingList("k 1");

    expect(result).toEqual({ ok: true, value: LIST });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/kitchens/k%201/shopping-list");
    expect(init.method).toBe("GET");
    expect(init.credentials).toBe("same-origin");
  });

  it("keeps the status and code of a refused call", async () => {
    fetchMock.mockResolvedValue(json({ code: "kitchen_not_found", detail: "x" }, 404));

    expect(await fetchShoppingList("k1")).toEqual({
      ok: false,
      status: 404,
      code: "kitchen_not_found",
    });
  });

  it("returns status 0 on a network failure", async () => {
    fetchMock.mockRejectedValue(new Error("offline"));

    expect(await fetchShoppingList("k1")).toEqual({ ok: false, status: 0, code: null });
  });

  it("rejects a body without a lines array", async () => {
    fetchMock.mockResolvedValue(json({ is_empty: false }));

    expect(await fetchShoppingList("k1")).toEqual({ ok: false, status: 200, code: null });
  });

  it("rejects a body without is_empty", async () => {
    fetchMock.mockResolvedValue(json({ lines: [], your_call: [] }));

    expect(await fetchShoppingList("k1")).toEqual({ ok: false, status: 200, code: null });
  });

  it("rejects a body that is not an object", async () => {
    fetchMock.mockResolvedValue(json(null));

    expect(await fetchShoppingList("k1")).toEqual({ ok: false, status: 200, code: null });
  });
});
