import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  addDraftItem,
  cartRecipeIds,
  discardCart,
  fetchCart,
  putCartDraft,
  removeDraftItem,
  saveCart,
  startCartEdit,
  type Cart,
} from "./cartClient";

const fetchMock = vi.fn();

const CART: Cart = {
  kitchen_id: "k1",
  entries: [],
  editor: null,
  draft: null,
  can_edit: true,
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

describe("cartClient", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  it.each([
    ["GET", () => fetchCart("k1"), "/api/kitchens/k1/cart"],
    ["POST", () => startCartEdit("k1"), "/api/kitchens/k1/cart/edit"],
    ["PUT", () => putCartDraft("k1", { items: [] }), "/api/kitchens/k1/cart/draft"],
    ["POST", () => addDraftItem("k1", "r1"), "/api/kitchens/k1/cart/draft/items"],
    ["DELETE", () => removeDraftItem("k1", "r1"), "/api/kitchens/k1/cart/draft/items/r1"],
    ["POST", () => saveCart("k1"), "/api/kitchens/k1/cart/save"],
  ])("%s %s answers the cart", async (method, run, url) => {
    fetchMock.mockResolvedValue(json(CART));
    const result = await run();
    expect(result).toEqual({ ok: true, value: CART });
    const [calledUrl, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(calledUrl).toBe(url);
    expect(init.method).toBe(method);
  });

  it("sends the recipe id when adding", async () => {
    fetchMock.mockResolvedValue(json(CART));
    await addDraftItem("k1", "r1");
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(JSON.stringify({ recipe_id: "r1" }));
  });

  it("discard answers true on 204", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    expect(await discardCart("k1")).toEqual({ ok: true, value: true });
  });

  it("keeps the code on 404", async () => {
    fetchMock.mockResolvedValue(json({ code: "kitchen_not_found" }, 404));
    expect(await fetchCart("k1")).toEqual({ ok: false, status: 404, code: "kitchen_not_found" });
  });

  it("keeps the editor alias on 409 cart_locked", async () => {
    fetchMock.mockResolvedValue(json({ code: "cart_locked", editor_alias: "ana" }, 409));
    expect(await startCartEdit("k1")).toEqual({
      ok: false,
      status: 409,
      code: "cart_locked",
      editorAlias: "ana",
    });
  });

  it("keeps the field on 422", async () => {
    fetchMock.mockResolvedValue(json({ code: "invalid_value", field: "servings" }, 422));
    const result = await putCartDraft("k1", { items: [] });
    expect(result).toEqual({ ok: false, status: 422, code: "invalid_value", field: "servings" });
  });

  it("answers status 0 on a network failure", async () => {
    fetchMock.mockRejectedValue(new Error("down"));
    expect(await fetchCart("k1")).toEqual({ ok: false, status: 0, code: null });
  });

  it("reads my draft's recipes while I edit, else the saved ones", () => {
    const entry = (id: string) => ({
      recipe_id: id,
      title: id,
      notebook_id: "n",
      notebook_name: "N",
      base_servings: 4,
      servings: 1,
      factor: "0.5",
    });
    const saved = { ...CART, entries: [entry("a")] };
    expect([...cartRecipeIds(saved)]).toEqual(["a"]);
    const mine = {
      ...saved,
      editor: { alias: "ana", is_me: true, idle_expires_at: null },
      draft: { entries: [entry("b")], dropped_recipe_ids: [] },
    };
    expect([...cartRecipeIds(mine)]).toEqual(["b"]);
  });
});
