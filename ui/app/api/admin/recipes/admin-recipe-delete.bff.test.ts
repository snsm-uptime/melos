import { beforeEach, describe, expect, it, vi } from "vitest";

const { fetchMock } = vi.hoisted(() => ({ fetchMock: vi.fn() }));
vi.stubGlobal("fetch", fetchMock);

import { DELETE } from "./[recipeId]/route";

const ID = "6f1c2a9e-2b1d-4c1e-9d3a-0a1b2c3d4e5f";

function call(recipeId: string) {
  const request = new Request(`http://ui/api/admin/recipes/${recipeId}`, {
    method: "DELETE",
    headers: { cookie: "melos_session=tok" },
  });
  return DELETE(request as never, { params: Promise.resolve({ recipeId }) });
}

describe("admin recipe delete BFF (spec 055)", () => {
  beforeEach(() => fetchMock.mockReset());

  it("forwards the delete with the caller's cookie and passes the 204 through", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    const response = await call(ID);
    expect(response.status).toBe(204);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url.endsWith(`/admin/recipes/${ID}`)).toBe(true);
    expect(init.method).toBe("DELETE");
    expect(new Headers(init.headers).get("Cookie")).toBe("melos_session=tok");
  });

  it("passes the api's refusal through", async () => {
    fetchMock.mockResolvedValue(
      new Response('{"detail":"Not Found"}', { status: 404 }),
    );
    expect((await call(ID)).status).toBe(404);
  });
});
