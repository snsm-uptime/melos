import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  addShoppingItem,
  closeShoppingList,
  fetchClosedList,
  fetchClosedLists,
  fetchShoppingList,
  localDate,
  removeShoppingItem,
  type ShoppingList,
} from "./shoppingListClient";

const fetchMock = vi.fn();

const LIST: ShoppingList = {
  is_empty: false,
  status: "active",
  list_id: "l1",
  kitchen_is_archived: false,
  hand_items: [],
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

describe("saved list calls", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("POSTs a new item and returns the list", async () => {
    fetchMock.mockResolvedValue(json(LIST, 201));
    const result = await addShoppingItem("k1", { name: "soap" });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/kitchens/k1/shopping-list/items");
    expect(init.method).toBe("POST");
    expect(init.body).toBe('{"name":"soap"}');
    expect(result).toEqual({ ok: true, value: LIST });
  });

  it("DELETEs an item", async () => {
    fetchMock.mockResolvedValue(json(LIST));
    await removeShoppingItem("k1", "i/1");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/kitchens/k1/shopping-list/items/i%2F1");
  });

  it("keeps the code of a refused Done", async () => {
    fetchMock.mockResolvedValue(json({ code: "list_empty" }, 409));
    expect(await closeShoppingList("k1", "l1")).toEqual({
      ok: false,
      status: 409,
      code: "list_empty",
    });
  });

  it("sends the member's own day with Done", async () => {
    fetchMock.mockResolvedValue(json({ id: "l1", closing_date: "2026-10-30" }));
    await closeShoppingList("k1", "l1");
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({
      list_id: "l1",
      closing_date: localDate(),
    });
  });

  it("reads the local calendar, padded", () => {
    expect(localDate(new Date(2026, 0, 5, 23, 30))).toBe("2026-01-05");
  });

  it("reads closed lists", async () => {
    fetchMock.mockResolvedValue(json({ items: [] }));
    expect(await fetchClosedLists("k1")).toEqual({ ok: true, value: [] });
    fetchMock.mockResolvedValue(json({ id: "l1", closing_date: "2026-10-30" }));
    expect(await fetchClosedList("k1", "l1")).toEqual({
      ok: true,
      value: { id: "l1", closing_date: "2026-10-30", lines: [], your_call: [], hand_items: [] },
    });
  });
});
