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

const NB = "nb-1";

describe("catalog BFF routes (spec 043)", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockImplementation(async () => new Response("{}", { status: 200 }));
    process.env.API_INTERNAL_URL = "http://api.test:8000";
  });

  it("GET a notebook's catalog with the session cookie", async () => {
    const { GET } = await import("./notebooks/[notebookId]/catalog/route");
    await GET(request("GET"), { params: Promise.resolve({ notebookId: NB }) });
    const [url, init] = sent();
    expect(url).toBe("http://api.test:8000/notebooks/nb-1/catalog");
    expect(new Headers(init.headers).get("cookie")).toBe("melos_session=tok");
  });

  it("PATCH and DELETE encode the name; a 204 stays empty", async () => {
    const { PATCH, DELETE } = await import("./notebooks/[notebookId]/catalog/[name]/route");
    await PATCH(request("PATCH", { new_name: "tomato" }), {
      params: Promise.resolve({ notebookId: NB, name: "red pepper/hot" }),
    });
    expect(sent()[0]).toBe("http://api.test:8000/notebooks/nb-1/catalog/red%20pepper%2Fhot");
    expect(sent()[1].body).toBe('{"new_name":"tomato"}');
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    const gone = await DELETE(request("DELETE"), {
      params: Promise.resolve({ notebookId: NB, name: "saffron" }),
    });
    expect(gone.status).toBe(204);
    expect(sent()[1].method).toBe("DELETE");
  });

  it("a 409 body comes back unchanged", async () => {
    fetchMock.mockResolvedValue(
      new Response('{"code":"name_exists","existing":"tomato"}', { status: 409 }),
    );
    const { PATCH } = await import("./notebooks/[notebookId]/catalog/[name]/route");
    const response = await PATCH(request("PATCH", { new_name: "tomatoes" }), {
      params: Promise.resolve({ notebookId: NB, name: "tomatoe" }),
    });
    expect(response.status).toBe(409);
    expect(await response.json()).toEqual({ code: "name_exists", existing: "tomato" });
  });

  it("split, pair suggestions and dismissals", async () => {
    const split = await import("./notebooks/[notebookId]/catalog/[name]/split/route");
    await split.POST(request("POST", { other_name: "cebolla" }), {
      params: Promise.resolve({ notebookId: NB, name: "onion" }),
    });
    expect(sent()[0]).toBe("http://api.test:8000/notebooks/nb-1/catalog/onion/split");
    fetchMock.mockClear();
    const pairs = await import("./notebooks/[notebookId]/catalog/pair-suggestions/route");
    await pairs.POST(request("POST"), { params: Promise.resolve({ notebookId: NB }) });
    expect(sent()[0]).toBe("http://api.test:8000/notebooks/nb-1/catalog/pair-suggestions");
    expect(sent()[1].body).toBeUndefined();
    fetchMock.mockClear();
    const dismiss = await import("./notebooks/[notebookId]/catalog/pair-dismissals/route");
    await dismiss.POST(request("POST", { en: "garlic", es: "ajo" }), {
      params: Promise.resolve({ notebookId: NB }),
    });
    expect(sent()[0]).toBe("http://api.test:8000/notebooks/nb-1/catalog/pair-dismissals");
    expect(sent()[1].body).toBe('{"en":"garlic","es":"ajo"}');
  });

  it("merge preview and merge", async () => {
    const preview = await import("./catalog/merge-preview/route");
    await preview.POST(request("POST", { from_notebook_id: NB, merged: "cebolla", kept: "onion" }));
    expect(sent()[0]).toBe("http://api.test:8000/catalog/merge-preview");
    fetchMock.mockClear();
    const merge = await import("./catalog/merge/route");
    await merge.POST(request("POST", { merged: "cebolla", kept: "onion", notebook_ids: [NB] }));
    expect(sent()[0]).toBe("http://api.test:8000/catalog/merge");
    expect(sent()[1].method).toBe("POST");
  });

  it("a recipe's language", async () => {
    const { PATCH } = await import("./recipes/[recipeId]/language/route");
    await PATCH(request("PATCH", { language: "es" }), {
      params: Promise.resolve({ recipeId: "r-1" }),
    });
    expect(sent()[0]).toBe("http://api.test:8000/recipes/r-1/language");
    expect(sent()[1].body).toBe('{"language":"es"}');
  });
});
