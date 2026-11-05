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

describe("places BFF routes (spec 070)", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockImplementation(async () => new Response("{}", { status: 200 }));
    process.env.API_INTERNAL_URL = "http://api.test:8000";
  });

  it("GET and POST /me/places", async () => {
    const { GET, POST } = await import("./places/route");
    await GET(request("GET"));
    expect(sent()[0]).toBe("http://api.test:8000/me/places");
    fetchMock.mockClear();
    await POST(request("POST", { name: "Deli" }));
    const [url, init] = sent();
    expect(url).toBe("http://api.test:8000/me/places");
    expect(init.body).toBe('{"name":"Deli"}');
    expect(new Headers(init.headers).get("cookie")).toBe("melos_session=tok");
  });

  it("PATCH and DELETE encode the place id; a 204 stays empty", async () => {
    const { PATCH, DELETE } = await import("./places/[placeId]/route");
    await PATCH(request("PATCH", { name: "Deli" }), {
      params: Promise.resolve({ placeId: "a/b" }),
    });
    expect(sent()[0]).toBe("http://api.test:8000/me/places/a%2Fb");
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    const gone = await DELETE(request("DELETE"), { params: Promise.resolve({ placeId: "p1" }) });
    expect(gone.status).toBe(204);
    expect(sent()[1].method).toBe("DELETE");
  });

  it("ingredient places, sources and copy", async () => {
    const ingredients = await import("./ingredient-places/route");
    await ingredients.PUT(
      request("PUT", { name: "tomato", place: { kind: "default", key: "bakery" } }),
    );
    expect(sent()[0]).toBe("http://api.test:8000/me/ingredient-places");
    expect(sent()[1].method).toBe("PUT");
    fetchMock.mockClear();
    const sources = await import("./place-sources/route");
    await sources.GET(request("GET"));
    expect(sent()[0]).toBe("http://api.test:8000/me/place-sources");
    fetchMock.mockClear();
    const copy = await import("./places/copy/route");
    await copy.POST(request("POST", { source_user_id: "u1" }));
    expect(sent()[0]).toBe("http://api.test:8000/me/places/copy");
  });

  it("an unreachable api answers 502", async () => {
    fetchMock.mockRejectedValue(new Error("down"));
    const { GET } = await import("./places/route");
    expect((await GET(request("GET"))).status).toBe(502);
  });
});
