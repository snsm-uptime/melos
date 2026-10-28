import { beforeEach, describe, expect, it, vi } from "vitest";

const { fetchMock } = vi.hoisted(() => ({ fetchMock: vi.fn() }));
vi.stubGlobal("fetch", fetchMock);

describe("kitchen recipes BFF", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    process.env.API_INTERNAL_URL = "http://api.test:8000";
  });

  it("forwards page, q and the cookie, and returns the api answer", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const { GET } = await import("./route");
    const request = new Request("http://localhost/x?page=2&q=soup&other=1", {
      headers: { cookie: "melos_session=tok" },
    }) as never;

    const response = await GET(request, { params: Promise.resolve({ kitchenId: "id1" }) });

    expect(response.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test:8000/notebooks/kitchens/id1/recipes?page=2&q=soup");
    expect(new Headers(init.headers).get("Cookie")).toBe("melos_session=tok");
  });

  it("passes a 404 through unchanged", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ code: "x" }), { status: 404 }));
    const { GET } = await import("./route");
    const response = await GET(new Request("http://localhost/x") as never, {
      params: Promise.resolve({ kitchenId: "id1" }),
    });
    expect(response.status).toBe(404);
  });

  it("answers 502 when the api is unreachable", async () => {
    fetchMock.mockRejectedValue(new Error("down"));
    const { GET } = await import("./route");
    const response = await GET(new Request("http://localhost/x") as never, {
      params: Promise.resolve({ kitchenId: "id1" }),
    });
    expect(response.status).toBe(502);
  });
});
