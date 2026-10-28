import { beforeEach, describe, expect, it, vi } from "vitest";

const { fetchMock } = vi.hoisted(() => ({
  fetchMock: vi.fn(),
}));

vi.stubGlobal("fetch", fetchMock);

import { POST } from "./route";

describe("POST /api/auth/sign-out BFF", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    process.env.API_INTERNAL_URL = "http://api.test:8000";
    delete process.env.SESSION_COOKIE_SECURE;
  });

  it("forwards Cookie header and clears melos_session on the browser response", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    const request = new Request("http://localhost/api/auth/sign-out", {
      method: "POST",
      headers: { cookie: "melos_session=tok" },
    });

    const response = await POST(request as never);
    expect(response.status).toBe(204);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test:8000/auth/sign-out",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Cookie: "melos_session=tok" }),
      }),
    );
    const setCookie = response.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain("melos_session=");
    expect(setCookie.toLowerCase()).toMatch(/max-age=0/);
  });

  it("still clears melos_session when upstream fetch throws", async () => {
    fetchMock.mockRejectedValue(new Error("upstream down"));

    const response = await POST(
      new Request("http://localhost/api/auth/sign-out", {
        method: "POST",
        headers: { cookie: "melos_session=stale" },
      }) as never,
    );

    expect(response.status).toBe(204);
    const setCookie = response.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain("melos_session=");
    expect(setCookie.toLowerCase()).toMatch(/max-age=0/);
  });

  it("also ends the signed-out language pick (spec 063 FR-013), even when upstream fails", async () => {
    for (const upstream of [() => new Response(null, { status: 204 }), () => Promise.reject(new Error("down"))]) {
      fetchMock.mockReset();
      fetchMock.mockImplementation(async () => upstream());
      const response = await POST(
        new Request("http://localhost/api/auth/sign-out", {
          method: "POST",
          headers: { cookie: "melos_session=tok; melos_lang=en" },
        }) as never,
      );
      const cookies = response.headers.getSetCookie();
      const lang = cookies.find((cookie) => cookie.startsWith("melos_lang="));
      expect(lang).toBeTruthy();
      expect(lang!.toLowerCase()).toMatch(/max-age=0/);
      expect(cookies.some((cookie) => cookie.startsWith("melos_session="))).toBe(true);
    }
  });
});
