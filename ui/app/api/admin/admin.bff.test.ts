import { beforeEach, describe, expect, it, vi } from "vitest";

const { fetchMock } = vi.hoisted(() => ({ fetchMock: vi.fn() }));
vi.stubGlobal("fetch", fetchMock);

import { GET } from "./[section]/route";

function call(section: string) {
  const request = new Request(`http://ui/api/admin/${section}`, {
    headers: { cookie: "melos_session=tok" },
  });
  return GET(request as never, { params: Promise.resolve({ section }) });
}

describe("admin BFF (spec 055)", () => {
  beforeEach(() => fetchMock.mockReset());

  it.each(["units", "ingredients", "recipes", "users", "refused-sites"])("passes %s through", async (section) => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ [section]: [] }), { status: 200 }));
    const response = await call(section);
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ [section]: [] });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url.endsWith(`/admin/${section}`)).toBe(true);
    expect(new Headers(init.headers).get("Cookie")).toBe("melos_session=tok");
  });

  it("answers 404 to anything else, with no upstream call", async () => {
    const response = await call("sessions");
    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("passes the api's 404 through", async () => {
    fetchMock.mockResolvedValue(new Response('{"detail":"Not Found"}', { status: 404 }));
    expect((await call("units")).status).toBe(404);
  });
});
