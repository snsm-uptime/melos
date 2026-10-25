import { beforeEach, describe, expect, it, vi } from "vitest";

const { fetchMock } = vi.hoisted(() => ({
  fetchMock: vi.fn(),
}));

vi.stubGlobal("fetch", fetchMock);

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function get(url: string) {
  return new Request(url, {
    headers: { cookie: "melos_session=tok" },
  }) as never;
}

function forwardedCookie(): string | null {
  const init = fetchMock.mock.calls[0][1] as RequestInit;
  return new Headers(init.headers).get("Cookie");
}

const notebook = {
  id: "n1",
  name: "ana's Notebook",
  kind: "personal",
  access: "owner",
  owner_alias: "ana",
  kitchen_id: null,
  kitchen_is_archived: null,
  is_default: true,
};

describe("notebooks BFF", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    process.env.API_INTERNAL_URL = "http://api.test:8000";
  });

  it("GET /api/notebooks forwards cookie and the list", async () => {
    const body = { notebooks: [notebook] };
    fetchMock.mockResolvedValue(json(body));
    const { GET } = await import("@/app/api/notebooks/route");

    const response = await GET(get("http://localhost/api/notebooks"));

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(body);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test:8000/notebooks",
      expect.objectContaining({ method: "GET" }),
    );
    expect(forwardedCookie()).toBe("melos_session=tok");
  });

  it("GET /api/notebooks/default forwards to the default route", async () => {
    fetchMock.mockResolvedValue(json(notebook));
    const { GET } = await import("@/app/api/notebooks/default/route");

    const response = await GET(get("http://localhost/api/notebooks/default"));

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(notebook);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test:8000/notebooks/default",
      expect.objectContaining({ method: "GET" }),
    );
    expect(forwardedCookie()).toBe("melos_session=tok");
  });

  it("GET /api/notebooks/[notebookId] passes a 404 through", async () => {
    const notFound = {
      detail: "Notebook not found.",
      code: "notebook_not_found",
    };
    fetchMock.mockResolvedValue(json(notFound, 404));
    const { GET } = await import("@/app/api/notebooks/[notebookId]/route");

    const response = await GET(get("http://localhost/api/notebooks/n9"), {
      params: Promise.resolve({ notebookId: "n9" }),
    });

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual(notFound);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test:8000/notebooks/n9",
      expect.objectContaining({ method: "GET" }),
    );
    expect(forwardedCookie()).toBe("melos_session=tok");
  });

  it("GET /api/notebooks/kitchens/[kitchenId] forwards cookie and the list", async () => {
    const body = {
      notebooks: [
        {
          ...notebook,
          id: "n2",
          name: "ana's (Home) Notebook",
          kind: "kitchen",
          access: "kitchen_member",
          kitchen_id: "k1",
          kitchen_is_archived: false,
          is_default: false,
        },
      ],
    };
    fetchMock.mockResolvedValue(json(body));
    const { GET } = await import("@/app/api/notebooks/kitchens/[kitchenId]/route");

    const response = await GET(get("http://localhost/api/notebooks/kitchens/k1"), {
      params: Promise.resolve({ kitchenId: "k1" }),
    });

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(body);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test:8000/notebooks/kitchens/k1",
      expect.objectContaining({ method: "GET" }),
    );
    expect(forwardedCookie()).toBe("melos_session=tok");
  });

  it("returns 502 when the api is unreachable", async () => {
    fetchMock.mockRejectedValue(new Error("down"));
    const { GET } = await import("@/app/api/notebooks/default/route");

    const response = await GET(get("http://localhost/api/notebooks/default"));

    expect(response.status).toBe(502);
    expect((await response.json()).code).toBe("bad_gateway");
  });
});
