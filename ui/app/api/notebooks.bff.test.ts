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
  recipe_count: 0,
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

  function write(url: string, method: string, body?: unknown) {
    return new Request(url, {
      method,
      headers: { cookie: "melos_session=tok", "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }) as never;
  }

  it("PATCH /api/notebooks/[notebookId] forwards the name, cookie and status", async () => {
    fetchMock.mockResolvedValue(json(notebook));
    const { PATCH } = await import("@/app/api/notebooks/[notebookId]/route");

    const response = await PATCH(
      write("http://localhost/api/notebooks/n1", "PATCH", { name: "Soups" }),
      { params: Promise.resolve({ notebookId: "n1" }) },
    );

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test:8000/notebooks/n1",
      expect.objectContaining({ method: "PATCH", body: JSON.stringify({ name: "Soups" }) }),
    );
    expect(forwardedCookie()).toBe("melos_session=tok");
  });

  it("PATCH answers 502 when the api cannot be reached", async () => {
    fetchMock.mockRejectedValue(new TypeError("fetch failed"));
    const { PATCH } = await import("@/app/api/notebooks/[notebookId]/route");

    const response = await PATCH(
      write("http://localhost/api/notebooks/n1", "PATCH", { name: "Soups" }),
      { params: Promise.resolve({ notebookId: "n1" }) },
    );

    expect(response.status).toBe(502);
    expect((await response.json()).code).toBe("bad_gateway");
  });

  it("DELETE /api/notebooks/[notebookId] passes a 204 through with no body", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    const { DELETE } = await import("@/app/api/notebooks/[notebookId]/route");

    const response = await DELETE(write("http://localhost/api/notebooks/n1", "DELETE"), {
      params: Promise.resolve({ notebookId: "n1" }),
    });

    expect(response.status).toBe(204);
    expect(await response.text()).toBe("");
    expect(forwardedCookie()).toBe("melos_session=tok");
  });

  it("POST /api/notebooks/kitchens/[kitchenId] forwards the name", async () => {
    fetchMock.mockResolvedValue(json(notebook, 201));
    const { POST } = await import("@/app/api/notebooks/kitchens/[kitchenId]/route");

    const response = await POST(
      write("http://localhost/api/notebooks/kitchens/k1", "POST", { name: "Holidays" }),
      { params: Promise.resolve({ kitchenId: "k1" }) },
    );

    expect(response.status).toBe(201);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test:8000/notebooks/kitchens/k1",
      expect.objectContaining({ method: "POST" }),
    );
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
          recipe_count: 0,
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

  it("POST snapshots forwards cookie and body, and passes the status through", async () => {
    fetchMock.mockResolvedValue(json({ ...notebook, id: "snap" }, 201));
    const { POST } = await import("@/app/api/notebooks/kitchens/[kitchenId]/snapshots/route");
    const body = JSON.stringify({ source_notebook_id: "n1", snapshot_key: "key" });

    const response = await POST(
      new Request("http://localhost/api/notebooks/kitchens/k1/snapshots", {
        method: "POST",
        headers: { cookie: "melos_session=tok" },
        body,
      }) as never,
      { params: Promise.resolve({ kitchenId: "k1" }) },
    );

    expect(response.status).toBe(201);
    expect(fetchMock.mock.calls[0][0]).toBe("http://api.test:8000/notebooks/kitchens/k1/snapshots");
    expect((fetchMock.mock.calls[0][1] as RequestInit).body).toBe(body);
    expect(forwardedCookie()).toBe("melos_session=tok");
  });

  it("POST snapshots passes a 409 and its code through", async () => {
    fetchMock.mockResolvedValue(json({ code: "snapshot_exists" }, 409));
    const { POST } = await import("@/app/api/notebooks/kitchens/[kitchenId]/snapshots/route");

    const response = await POST(
      new Request("http://localhost/x", { method: "POST", body: "{}" }) as never,
      { params: Promise.resolve({ kitchenId: "k1" }) },
    );

    expect(response.status).toBe(409);
    expect(await response.json()).toEqual({ code: "snapshot_exists" });
  });

  it("POST capture-notebook forwards the cookie", async () => {
    fetchMock.mockResolvedValue(json(notebook));
    const { POST } = await import(
      "@/app/api/notebooks/kitchens/[kitchenId]/capture-notebook/route"
    );

    const response = await POST(get("http://localhost/x"), {
      params: Promise.resolve({ kitchenId: "k1" }),
    });

    expect(response.status).toBe(200);
    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://api.test:8000/notebooks/kitchens/k1/capture-notebook",
    );
    expect((fetchMock.mock.calls[0][1] as RequestInit).method).toBe("POST");
    expect(forwardedCookie()).toBe("melos_session=tok");
  });

  it("both new POST routes answer 502 when the api is unreachable", async () => {
    fetchMock.mockRejectedValue(new Error("down"));
    const snapshots = await import("@/app/api/notebooks/kitchens/[kitchenId]/snapshots/route");
    const capture = await import(
      "@/app/api/notebooks/kitchens/[kitchenId]/capture-notebook/route"
    );
    const params = { params: Promise.resolve({ kitchenId: "k1" }) };

    for (const POST of [snapshots.POST, capture.POST]) {
      const response = await POST(
        new Request("http://localhost/x", { method: "POST", body: "{}" }) as never,
        params,
      );
      expect(response.status).toBe(502);
      expect(await response.json()).toMatchObject({ code: "bad_gateway" });
    }
  });

  it("returns 502 when the api is unreachable", async () => {
    fetchMock.mockRejectedValue(new Error("down"));
    const { GET } = await import("@/app/api/notebooks/default/route");

    const response = await GET(get("http://localhost/api/notebooks/default"));

    expect(response.status).toBe(502);
    expect((await response.json()).code).toBe("bad_gateway");
  });

  it("POST /api/notebooks forwards the name and the cookie", async () => {
    fetchMock.mockResolvedValue(json(notebook, 201));
    const { POST } = await import("@/app/api/notebooks/route");

    const response = await POST(
      new Request("http://localhost/api/notebooks", {
        method: "POST",
        headers: { cookie: "melos_session=tok", "Content-Type": "application/json" },
        body: JSON.stringify({ name: "Postres" }),
      }) as never,
    );

    expect(response.status).toBe(201);
    expect(fetchMock.mock.calls[0][0]).toBe("http://api.test:8000/notebooks");
    expect((fetchMock.mock.calls[0][1] as RequestInit).body).toBe(
      JSON.stringify({ name: "Postres" }),
    );
    expect(forwardedCookie()).toBe("melos_session=tok");
  });

  describe("sharing routes (spec 057)", () => {
    const ctx = { params: Promise.resolve({ notebookId: "n1" }) };
    const send = (url: string, method: string, body?: unknown) =>
      new Request(url, {
        method,
        headers: { cookie: "melos_session=tok", "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      }) as never;

    it("POST invites forwards the body, the cookie and the answer", async () => {
      fetchMock.mockResolvedValue(json({ status: "sent" }, 201));
      const { POST } = await import("@/app/api/notebooks/[notebookId]/invites/route");

      const response = await POST(
        send("http://localhost/api/notebooks/n1/invites", "POST", { email: "b@x.test" }),
        ctx,
      );

      expect(response.status).toBe(201);
      expect(fetchMock.mock.calls[0][0]).toBe("http://api.test:8000/notebooks/n1/invites");
      expect((fetchMock.mock.calls[0][1] as RequestInit).body).toBe(
        JSON.stringify({ email: "b@x.test" }),
      );
      expect(forwardedCookie()).toBe("melos_session=tok");
    });

    it("GET invites passes a refusal through", async () => {
      fetchMock.mockResolvedValue(json({ code: "notebook_owner_only" }, 403));
      const { GET } = await import("@/app/api/notebooks/[notebookId]/invites/route");
      const response = await GET(get("http://localhost/api/notebooks/n1/invites"), ctx);
      expect(response.status).toBe(403);
      expect(await response.json()).toEqual({ code: "notebook_owner_only" });
    });

    it("answers 502 when the api can't be reached", async () => {
      fetchMock.mockRejectedValue(new Error("down"));
      const { GET } = await import("@/app/api/notebooks/[notebookId]/members/route");
      const response = await GET(get("http://localhost/api/notebooks/n1/members"), ctx);
      expect(response.status).toBe(502);
      expect((await response.json()).code).toBe("bad_gateway");
    });

    it("DELETE invite keeps a 204 empty", async () => {
      fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
      const { DELETE } = await import(
        "@/app/api/notebooks/[notebookId]/invites/[inviteId]/route"
      );
      const response = await DELETE(send("http://localhost/x", "DELETE"), {
        params: Promise.resolve({ notebookId: "n1", inviteId: "i1" }),
      });
      expect(response.status).toBe(204);
      expect(fetchMock.mock.calls[0][0]).toBe("http://api.test:8000/notebooks/n1/invites/i1");
    });

    it("POST resend goes to the invite's resend route", async () => {
      fetchMock.mockResolvedValue(json({ status: "sent" }));
      const { POST } = await import(
        "@/app/api/notebooks/[notebookId]/invites/[inviteId]/resend/route"
      );
      await POST(send("http://localhost/x", "POST"), {
        params: Promise.resolve({ notebookId: "n1", inviteId: "i1" }),
      });
      expect(fetchMock.mock.calls[0][0]).toBe(
        "http://api.test:8000/notebooks/n1/invites/i1/resend",
      );
    });

    it("DELETE members/me leaves", async () => {
      fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
      const { DELETE } = await import("@/app/api/notebooks/[notebookId]/members/me/route");
      const response = await DELETE(send("http://localhost/x", "DELETE"), ctx);
      expect(response.status).toBe(204);
      expect(fetchMock.mock.calls[0][0]).toBe("http://api.test:8000/notebooks/n1/members/me");
    });

    it("DELETE members/[userId] removes", async () => {
      fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
      const { DELETE } = await import("@/app/api/notebooks/[notebookId]/members/[userId]/route");
      await DELETE(send("http://localhost/x", "DELETE"), {
        params: Promise.resolve({ notebookId: "n1", userId: "u2" }),
      });
      expect(fetchMock.mock.calls[0][0]).toBe("http://api.test:8000/notebooks/n1/members/u2");
    });

    it("GET invite preview forwards the token and needs no session", async () => {
      fetchMock.mockResolvedValue(json({ notebook_name: "Recetas" }));
      const { GET } = await import("@/app/api/invites/notebook/preview/route");
      const request = Object.assign(new Request("http://localhost/x"), {
        nextUrl: new URL("http://localhost/api/invites/notebook/preview?token=a%20b"),
      });
      await GET(request as never);
      expect(fetchMock.mock.calls[0][0]).toBe(
        "http://api.test:8000/invites/notebook/preview?token=a+b",
      );
    });

    it("POST invite accept forwards the token and the cookie", async () => {
      fetchMock.mockResolvedValue(json({ notebook_id: "n1" }));
      const { POST } = await import("@/app/api/invites/notebook/accept/route");
      const response = await POST(send("http://localhost/x", "POST", { token: "t" }));
      expect(response.status).toBe(200);
      expect(fetchMock.mock.calls[0][0]).toBe("http://api.test:8000/invites/notebook/accept");
      expect(forwardedCookie()).toBe("melos_session=tok");
    });
  });
});
