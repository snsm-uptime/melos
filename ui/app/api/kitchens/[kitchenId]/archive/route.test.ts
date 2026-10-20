import { beforeEach, describe, expect, it, vi } from "vitest";

const { fetchMock } = vi.hoisted(() => ({
  fetchMock: vi.fn(),
}));

vi.stubGlobal("fetch", fetchMock);

import { POST } from "./route";

function context(kitchenId: string) {
  return { params: Promise.resolve({ kitchenId }) };
}

describe("POST /api/kitchens/{kitchenId}/archive BFF", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    process.env.API_INTERNAL_URL = "http://api.test:8000";
  });

  it("forwards the cookie and passes through the upstream archived kitchen", async () => {
    const body = { id: "l1", name: "Household", owner_id: "u1", is_archived: true };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const request = new Request("http://localhost/api/kitchens/l1/archive", {
      method: "POST",
      headers: { cookie: "melos_session=tok" },
    });

    const response = await POST(request as never, context("l1"));

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(body);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://api.test:8000/kitchens/l1/archive");
    expect(init.method).toBe("POST");
    expect((init.headers as Headers).get("Cookie")).toBe("melos_session=tok");
  });

  it("passes through a 403 (non-owner) upstream error", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not the kitchen owner.", code: "not_kitchen_owner" }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const request = new Request("http://localhost/api/kitchens/l1/archive", { method: "POST" });
    const response = await POST(request as never, context("l1"));

    expect(response.status).toBe(403);
    expect((await response.json()).code).toBe("not_kitchen_owner");
  });

  it("returns 502 bad_gateway when upstream is unavailable", async () => {
    fetchMock.mockRejectedValue(new Error("upstream down"));

    const request = new Request("http://localhost/api/kitchens/l1/archive", { method: "POST" });
    const response = await POST(request as never, context("l1"));

    expect(response.status).toBe(502);
    expect((await response.json()).code).toBe("bad_gateway");
  });
});
