import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchMock = vi.fn();

const context = { params: Promise.resolve({ kitchenId: "k1" }) };

function request(method: string) {
  return new Request("http://localhost/x", {
    method,
    headers: { cookie: "melos_session=tok", "Content-Type": "application/json" },
  }) as never;
}

describe("/api/kitchens/[kitchenId]/shopping-list BFF", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    process.env.API_INTERNAL_URL = "http://api.test:8000";
  });

  it("forwards GET with the cookie and passes 200 through", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ is_empty: true, lines: [], your_call: [] }), { status: 200 }),
    );
    const { GET } = await import("./route");

    const response = await GET(request("GET"), context);

    expect(response.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test:8000/kitchens/k1/shopping-list");
    expect(init.method).toBe("GET");
    expect(new Headers(init.headers).get("Cookie")).toBe("melos_session=tok");
  });

  it("passes a 404 through", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ code: "kitchen_not_found" }), { status: 404 }),
    );
    const { GET } = await import("./route");

    const response = await GET(request("GET"), context);

    expect(response.status).toBe(404);
  });
});
