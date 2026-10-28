import { beforeEach, describe, expect, it, vi } from "vitest";

const { fetchMock } = vi.hoisted(() => ({ fetchMock: vi.fn() }));
vi.stubGlobal("fetch", fetchMock);

const context = { params: Promise.resolve({ recipeId: "r1" }) };

function request(method: string, body?: unknown, cookie = "melos_session=tok") {
  return new Request("http://localhost/x", {
    method,
    headers: { cookie, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  }) as never;
}

describe("recipe BFF", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    process.env.API_INTERNAL_URL = "http://api.test:8000";
  });

  it("forwards a read with the cookie and returns the api answer", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ id: "r1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const { GET } = await import("./route");

    const response = await GET(request("GET"), context);

    expect(response.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test:8000/recipes/r1");
    expect(init.method).toBe("GET");
    expect(new Headers(init.headers).get("Cookie")).toBe("melos_session=tok");
  });

  it("forwards a replace with its body and passes a 409 through", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ code: "recipe_changed" }), { status: 409 }),
    );
    const { PUT } = await import("./route");

    const response = await PUT(request("PUT", { title: "x" }), context);

    expect(response.status).toBe(409);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("PUT");
    expect(init.body).toBe(JSON.stringify({ title: "x" }));
  });

  it("answers a delete with an empty 204", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    const { DELETE } = await import("./route");

    const response = await DELETE(request("DELETE"), context);

    expect(response.status).toBe(204);
    expect(await response.text()).toBe("");
  });

  it("answers 400 for a body that is not JSON", async () => {
    const { PUT } = await import("./route");
    const bad = new Request("http://localhost/x", { method: "PUT", body: "{nope" }) as never;

    const response = await PUT(bad, context);

    expect(response.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("answers a failed save as save_unavailable", async () => {
    fetchMock.mockRejectedValue(new Error("down"));
    const { PUT } = await import("./route");

    const response = await PUT(request("PUT", { title: "x" }), context);

    expect(response.status).toBe(503);
    expect((await response.json()).code).toBe("save_unavailable");
  });

  it("answers 502 when a read cannot reach the api", async () => {
    fetchMock.mockRejectedValue(new Error("down"));
    const { GET } = await import("./route");

    expect((await GET(request("GET"), context)).status).toBe(502);
  });
});
