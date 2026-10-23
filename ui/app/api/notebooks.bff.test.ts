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

describe("notebooks BFF", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    process.env.API_INTERNAL_URL = "http://api.test:8000";
  });

  it("GET /api/notebooks/kitchens/[kitchenId] forwards cookie and body", async () => {
    const body = {
      id: "n1",
      kind: "kitchen",
      kitchen_id: "k1",
      name: "Home",
      is_archived: false,
    };
    fetchMock.mockResolvedValue(json(body));
    const { GET } =
      await import("@/app/api/notebooks/kitchens/[kitchenId]/route");

    const response = await GET(
      get("http://localhost/api/notebooks/kitchens/k1"),
      {
        params: Promise.resolve({ kitchenId: "k1" }),
      },
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(body);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test:8000/notebooks/kitchens/k1",
      expect.objectContaining({ method: "GET" }),
    );
    expect(forwardedCookie()).toBe("melos_session=tok");
  });

  it("GET /api/notebooks/members/[userId] forwards to the default route", async () => {
    fetchMock.mockResolvedValue(
      json({ id: "n2", kind: "member", user_id: "u1" }),
    );
    const { GET } = await import("@/app/api/notebooks/members/[userId]/route");

    const response = await GET(
      get("http://localhost/api/notebooks/members/u1"),
      {
        params: Promise.resolve({ userId: "u1" }),
      },
    );

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test:8000/notebooks/members/u1",
      expect.objectContaining({ method: "GET" }),
    );
    expect(forwardedCookie()).toBe("melos_session=tok");
  });

  it("GET /api/notebooks/members/[userId]/[notebookId] passes a 404 through", async () => {
    const notFound = {
      detail: "Notebook not found.",
      code: "notebook_not_found",
    };
    fetchMock.mockResolvedValue(json(notFound, 404));
    const { GET } =
      await import("@/app/api/notebooks/members/[userId]/[notebookId]/route");

    const response = await GET(
      get("http://localhost/api/notebooks/members/u1/n9"),
      {
        params: Promise.resolve({ userId: "u1", notebookId: "n9" }),
      },
    );

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual(notFound);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test:8000/notebooks/members/u1/n9",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("returns 502 when the api is unreachable", async () => {
    fetchMock.mockRejectedValue(new Error("down"));
    const { GET } =
      await import("@/app/api/notebooks/kitchens/[kitchenId]/route");

    const response = await GET(
      get("http://localhost/api/notebooks/kitchens/k1"),
      {
        params: Promise.resolve({ kitchenId: "k1" }),
      },
    );

    expect(response.status).toBe(502);
    expect((await response.json()).code).toBe("bad_gateway");
  });
});
