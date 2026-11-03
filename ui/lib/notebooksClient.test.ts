import { afterEach, describe, expect, it, vi } from "vitest";

import {
  canManageNotebook,
  createKitchenNotebook,
  deleteNotebook,
  fetchDefaultNotebook,
  fetchKitchenNotebooks,
  fetchPersonalNotebooks,
  renameNotebook,
} from "./notebooksClient";

const notebook = {
  id: "nb-1",
  name: "ana's Notebook",
  kind: "personal",
  owner_alias: "ana",
  access: "owner",
  is_default: true,
  recipe_count: 0,
  kitchen_id: null,
  kitchen_is_archived: null,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubFetch(response: Partial<Response> & { json?: () => Promise<unknown> }) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("notebooksClient", () => {
  it("calls each BFF path", async () => {
    const fetchMock = stubFetch({
      ok: true,
      status: 200,
      json: async () => notebook,
    });
    await fetchDefaultNotebook();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/notebooks/default");

    stubFetch({ ok: true, status: 200, json: async () => ({ notebooks: [notebook] }) });
    const list = await fetchPersonalNotebooks();
    expect(list).toEqual({ ok: true, value: [notebook] });

    const kitchenFetch = stubFetch({
      ok: true,
      status: 200,
      json: async () => ({ notebooks: [] }),
    });
    await fetchKitchenNotebooks("kitchen 1");
    expect(kitchenFetch.mock.calls[0][0]).toBe("/api/notebooks/kitchens/kitchen%201");
  });

  it("returns a 403 alias_required as a typed error", async () => {
    stubFetch({
      ok: false,
      status: 403,
      json: async () => ({ code: "alias_required", detail: "Choose an alias." }),
    });
    await expect(fetchPersonalNotebooks()).resolves.toEqual({
      ok: false,
      status: 403,
      code: "alias_required",
    });
  });

  it("returns a 404 kitchen_not_found as a typed error", async () => {
    stubFetch({
      ok: false,
      status: 404,
      json: async () => ({ code: "kitchen_not_found", detail: "Kitchen not found." }),
    });
    await expect(fetchKitchenNotebooks("k-1")).resolves.toEqual({
      ok: false,
      status: 404,
      code: "kitchen_not_found",
    });
  });

  it("returns a network failure as an error, not as an empty list", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(fetchPersonalNotebooks()).resolves.toEqual({
      ok: false,
      status: 0,
      code: null,
    });
  });

  it("treats a malformed list as an error, not as an empty list", async () => {
    stubFetch({ ok: true, status: 200, json: async () => ({ unexpected: true }) });
    await expect(fetchPersonalNotebooks()).resolves.toEqual({
      ok: false,
      status: 200,
      code: null,
    });
  });

  it("renames with a PATCH carrying the name", async () => {
    const fetchMock = stubFetch({ ok: true, status: 200, json: async () => notebook });
    await expect(renameNotebook("nb-1", "Soups")).resolves.toEqual({ ok: true, value: notebook });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/notebooks/nb-1");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body as string)).toEqual({ name: "Soups" });
  });

  it("keeps the code of a refused rename", async () => {
    stubFetch({
      ok: false,
      status: 403,
      json: async () => ({ code: "notebook_owner_only" }),
    });
    await expect(renameNotebook("nb-1", "Soups")).resolves.toEqual({
      ok: false,
      status: 403,
      code: "notebook_owner_only",
    });
  });

  it("treats a 204 on delete as success", async () => {
    const fetchMock = stubFetch({ ok: true, status: 204 });
    await expect(deleteNotebook("nb-1")).resolves.toEqual({ ok: true, value: null });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/notebooks/nb-1");
    expect(init.method).toBe("DELETE");
  });

  it("adds a kitchen notebook with a POST to the kitchen", async () => {
    const fetchMock = stubFetch({ ok: true, status: 201, json: async () => notebook });
    await createKitchenNotebook("k1", "Holidays");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/notebooks/kitchens/k1");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ name: "Holidays" });
  });

  it.each([
    ["owner", null, true],
    ["member", null, false],
    ["kitchen_member", false, true],
    ["kitchen_member", true, false],
  ] as const)("canManageNotebook for %s, archived %s", (access, archived, expected) => {
    expect(canManageNotebook({ access, kitchen_is_archived: archived })).toBe(expected);
  });
});
