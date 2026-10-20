import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { fetchMock } = vi.hoisted(() => ({
  fetchMock: vi.fn(),
}));

vi.stubGlobal("fetch", fetchMock);

function okJson(body: unknown = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("kitchens / invites BFF smoke (coverage floor)", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    process.env.API_INTERNAL_URL = "http://api.test:8000";
    fetchMock.mockImplementation(() => Promise.resolve(okJson({})));
  });

  it("GET /api/kitchens forwards cookie", async () => {
    const { GET } = await import("@/app/api/kitchens/route");
    const response = await GET(
      new Request("http://localhost/api/kitchens", {
        headers: { cookie: "melos_session=tok" },
      }) as never,
    );
    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test:8000/kitchens",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("POST /api/kitchens forwards name", async () => {
    const { POST } = await import("@/app/api/kitchens/route");
    const response = await POST(
      new Request("http://localhost/api/kitchens", {
        method: "POST",
        headers: {
          cookie: "melos_session=tok",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: "Home" }),
      }) as never,
    );
    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test:8000/kitchens",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("GET/PATCH /api/kitchens/[kitchenId] forward", async () => {
    const mod = await import("@/app/api/kitchens/[kitchenId]/route");
    const ctx = { params: Promise.resolve({ kitchenId: "l1" }) };
    const getRes = await mod.GET(
      new Request("http://localhost/api/kitchens/l1", {
        headers: { cookie: "melos_session=tok" },
      }) as never,
      ctx,
    );
    expect(getRes.status).toBe(200);

    const patchRes = await mod.PATCH(
      new Request("http://localhost/api/kitchens/l1", {
        method: "PATCH",
        headers: {
          cookie: "melos_session=tok",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: "Renamed" }),
      }) as never,
      ctx,
    );
    expect(patchRes.status).toBe(200);
  });

  it("GET members forwards", async () => {
    const ctx = { params: Promise.resolve({ kitchenId: "l1" }) };
    const request = new Request("http://localhost/api/kitchens/l1/members", {
      headers: { cookie: "melos_session=tok" },
    }) as never;

    const members = await import("@/app/api/kitchens/[kitchenId]/members/route");
    expect((await members.GET(request, ctx)).status).toBe(200);
  });
  it("POST /api/kitchens/[kitchenId]/invites forwards email", async () => {
    const { POST } = await import("@/app/api/kitchens/[kitchenId]/invites/route");
    const response = await POST(
      new Request("http://localhost/api/kitchens/l1/invites", {
        method: "POST",
        headers: {
          cookie: "melos_session=tok",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email: "a@b.com" }),
      }) as never,
      { params: Promise.resolve({ kitchenId: "l1" }) },
    );
    expect(response.status).toBe(200);
  });

  it("invites preview GET and accept POST forward", async () => {
    const preview = await import("@/app/api/invites/preview/route");
    const previewRes = await preview.GET(
      new NextRequest("http://localhost/api/invites/preview?token=abc"),
    );
    expect(previewRes.status).toBe(200);
    const missingToken = await preview.GET(
      new NextRequest("http://localhost/api/invites/preview"),
    );
    expect(missingToken.status).toBe(200);

    const accept = await import("@/app/api/invites/accept/route");
    const acceptRes = await accept.POST(
      new Request("http://localhost/api/invites/accept", {
        method: "POST",
        headers: {
          cookie: "melos_session=tok",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ token: "abc" }),
      }) as never,
    );
    expect(acceptRes.status).toBe(200);
  });

  it("DELETE /api/kitchens/[kitchenId] forwards 204 and error bodies", async () => {
    const { DELETE } = await import("@/app/api/kitchens/[kitchenId]/route");
    const ctx = { params: Promise.resolve({ kitchenId: "l1" }) };
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    const gone = await DELETE(
      new Request("http://localhost/api/kitchens/l1", {
        method: "DELETE",
        headers: { cookie: "melos_session=tok" },
      }) as never,
      ctx,
    );
    expect(gone.status).toBe(204);

    fetchMock.mockResolvedValueOnce(
      new Response("still there", {
        status: 409,
        headers: { "Content-Type": "text/plain" },
      }),
    );
    const conflict = await DELETE(
      new Request("http://localhost/api/kitchens/l1", { method: "DELETE" }) as never,
      ctx,
    );
    expect(conflict.status).toBe(409);
    expect(await conflict.text()).toBe("still there");

    fetchMock.mockResolvedValueOnce(new Response("", { status: 400 }));
    const empty = await DELETE(
      new Request("http://localhost/api/kitchens/l1", { method: "DELETE" }) as never,
      ctx,
    );
    expect(empty.status).toBe(400);
  });

  it("returns 400/502 on kitchen mutation failures", async () => {
    const kitchen = await import("@/app/api/kitchens/[kitchenId]/route");
    const ctx = { params: Promise.resolve({ kitchenId: "l1" }) };
    const badJson = await kitchen.PATCH(
      new Request("http://localhost/api/kitchens/l1", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: "{not-json",
      }) as never,
      ctx,
    );
    expect(badJson.status).toBe(400);

    const unnamed = await kitchen.PATCH(
      new Request("http://localhost/api/kitchens/l1", {
        method: "PATCH",
        headers: {
          cookie: "melos_session=tok",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: 1 }),
      }) as never,
      ctx,
    );
    expect(unnamed.status).toBe(200);

    fetchMock.mockRejectedValueOnce(new Error("connection refused"));
    const failedGet = await kitchen.GET(
      new Request("http://localhost/api/kitchens/l1") as never,
      ctx,
    );
    expect(failedGet.status).toBe(502);

    fetchMock.mockRejectedValueOnce(new Error("connection refused"));
    const failedDelete = await kitchen.DELETE(
      new Request("http://localhost/api/kitchens/l1", { method: "DELETE" }) as never,
      ctx,
    );
    expect(failedDelete.status).toBe(502);
  });
});
