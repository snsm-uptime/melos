import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchDefaultNotebook,
  fetchKitchenNotebooks,
  fetchPersonalNotebooks,
} from "./notebooksClient";

const notebook = {
  id: "nb-1",
  name: "ana's Notebook",
  kind: "personal",
  owner_alias: "ana",
  access: "owner",
  is_default: true,
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
});
