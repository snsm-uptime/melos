import { beforeEach, describe, expect, it, vi } from "vitest";

const { fetchMock } = vi.hoisted(() => ({ fetchMock: vi.fn() }));
vi.stubGlobal("fetch", fetchMock);

describe("name matches BFF", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    process.env.API_INTERNAL_URL = "http://api.test:8000";
  });

  it("forwards the names and returns the matches", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ matches: [{ name: "onions", entry: "onion" }] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const { POST } = await import("./route");
    const request = new Request("http://localhost/x", {
      method: "POST",
      headers: { cookie: "melos_session=tok" },
      body: JSON.stringify({ names: ["onions"] }),
    }) as never;

    const response = await POST(request, { params: Promise.resolve({ recipeId: "r1" }) });

    expect(response.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test:8000/recipes/r1/name-matches");
    expect(init.body).toBe(JSON.stringify({ names: ["onions"] }));
  });

  it("passes a 403 through", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ code: "recipe_read_only" }), { status: 403 }));
    const { POST } = await import("./route");
    const request = new Request("http://localhost/x", {
      method: "POST",
      body: JSON.stringify({ names: ["a"] }),
    }) as never;

    const response = await POST(request, { params: Promise.resolve({ recipeId: "r1" }) });

    expect(response.status).toBe(403);
  });
});
