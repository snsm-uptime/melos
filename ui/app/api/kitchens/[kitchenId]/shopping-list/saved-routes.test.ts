import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchMock = vi.fn();

function request(method: string, body?: unknown) {
  return new Request("http://localhost/x", {
    method,
    headers: { cookie: "melos_session=tok", "Content-Type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  }) as never;
}

function sent() {
  return fetchMock.mock.calls[0] as [string, RequestInit];
}

describe("saved shopping list BFF routes (spec 025)", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockResolvedValue(new Response("{}", { status: 200 }));
    process.env.API_INTERNAL_URL = "http://api.test:8000";
  });

  it("POST items forwards the body", async () => {
    const { POST } = await import("./items/route");
    await POST(request("POST", { name: "soap" }), {
      params: Promise.resolve({ kitchenId: "k1" }),
    });
    const [url, init] = sent();
    expect(url).toBe("http://api.test:8000/kitchens/k1/shopping-list/items");
    expect(init.body).toBe('{"name":"soap"}');
  });

  it("DELETE an item encodes its id", async () => {
    const { DELETE } = await import("./items/[itemId]/route");
    await DELETE(request("DELETE"), {
      params: Promise.resolve({ kitchenId: "k1", itemId: "a/b" }),
    });
    expect(sent()[0]).toBe("http://api.test:8000/kitchens/k1/shopping-list/items/a%2Fb");
  });

  it("POST done forwards the list id and passes a 409 through", async () => {
    fetchMock.mockResolvedValue(new Response('{"code":"list_empty"}', { status: 409 }));
    const { POST } = await import("./done/route");
    const response = await POST(request("POST", { list_id: "l1" }), {
      params: Promise.resolve({ kitchenId: "k1" }),
    });
    expect(response.status).toBe(409);
    expect(sent()[0]).toBe("http://api.test:8000/kitchens/k1/shopping-list/done");
  });

  it("GET closed lists and one closed list", async () => {
    const { GET } = await import("../shopping-lists/route");
    await GET(request("GET"), { params: Promise.resolve({ kitchenId: "k1" }) });
    expect(sent()[0]).toBe("http://api.test:8000/kitchens/k1/shopping-lists");

    fetchMock.mockClear();
    fetchMock.mockResolvedValue(new Response("{}", { status: 200 }));
    const one = await import("../shopping-lists/[listId]/route");
    await one.GET(request("GET"), {
      params: Promise.resolve({ kitchenId: "k1", listId: "l1" }),
    });
    expect(sent()[0]).toBe("http://api.test:8000/kitchens/k1/shopping-lists/l1");
  });
});
