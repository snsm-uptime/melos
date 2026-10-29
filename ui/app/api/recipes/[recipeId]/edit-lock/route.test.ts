import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchMock = vi.fn();

const context = { params: Promise.resolve({ recipeId: "r1" }) };

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

describe("/api/recipes/[recipeId]/edit-lock BFF", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    process.env.API_INTERNAL_URL = "http://api.test:8000";
  });

  it("forwards POST with the cookie and passes 409 through", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ code: "x" }), { status: 409 }),
    );
    const { POST } = await import("./route");

    const response = await POST(request("POST"), context);

    expect(response.status).toBe(409);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test:8000/recipes/r1/edit-lock");
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("Cookie")).toBe("melos_session=tok");
  });

  it("forwards DELETE with the cookie and passes 204 through", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    const { DELETE } = await import("./route");

    const response = await DELETE(request("DELETE"), context);

    expect(response.status).toBe(204);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test:8000/recipes/r1/edit-lock");
    expect(init.method).toBe("DELETE");
    expect(new Headers(init.headers).get("Cookie")).toBe("melos_session=tok");
  });
});
