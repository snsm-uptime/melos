import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchMock = vi.fn();

const context = { params: Promise.resolve({ kitchenId: "k1" }) };

function request(method: string, body?: unknown) {
  return new Request("http://localhost/x", {
    method,
    headers: {
      cookie: "melos_session=tok",
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  }) as never;
}

describe("/api/kitchens/[kitchenId]/cart/draft/items BFF", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    process.env.API_INTERNAL_URL = "http://api.test:8000";
  });

  it("forwards POST with the cookie and passes 200 through", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ code: "x" }), { status: 200 }),
    );
    const { POST } = await import("./route");

    const response = await POST(request("POST", { recipe_id: "r1" }), context);

    expect(response.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test:8000/kitchens/k1/cart/draft/items");
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("Cookie")).toBe("melos_session=tok");
    expect(init.body).toBe(JSON.stringify({ recipe_id: "r1" }));
  });
});
