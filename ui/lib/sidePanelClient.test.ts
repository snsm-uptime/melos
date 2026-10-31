import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchSidePanel,
  requestSidePanelRefresh,
  setDefaultKitchen,
  subscribeSidePanelRefresh,
} from "./sidePanelClient";

const body = { default_kitchen_id: "k1", recipes_added: 5, notebooks: 2 };

afterEach(() => vi.unstubAllGlobals());

describe("sidePanelClient", () => {
  it("reads the panel data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body))));
    expect(await fetchSidePanel()).toEqual(body);
  });

  it("gives null on an error, so no wrong number shows", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 500 })));
    expect(await fetchSidePanel()).toBeNull();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    expect(await fetchSidePanel()).toBeNull();
  });

  it("sends the chosen kitchen", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(body)));
    vi.stubGlobal("fetch", fetchMock);
    expect(await setDefaultKitchen("k1")).toEqual(body);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/side-panel/default-kitchen");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body)).toEqual({ kitchen_id: "k1" });
  });

  it("tells subscribers to reload until they leave", () => {
    const listener = vi.fn();
    const leave = subscribeSidePanelRefresh(listener);
    requestSidePanelRefresh();
    leave();
    requestSidePanelRefresh();
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
