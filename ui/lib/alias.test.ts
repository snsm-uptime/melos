import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { cookieStore, fetchMock } = vi.hoisted(() => ({
  cookieStore: new Map<string, string>(),
  fetchMock: vi.fn(),
}));

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => (cookieStore.has(name) ? { name, value: cookieStore.get(name) } : undefined),
    getAll: () => [...cookieStore].map(([name, value]) => ({ name, value })),
  }),
}));
vi.mock("next/navigation", () => ({ redirect: vi.fn() }));
vi.stubGlobal("fetch", fetchMock);

function me(body: Record<string, unknown>) {
  fetchMock.mockResolvedValue(new Response(JSON.stringify(body), { status: 200 }));
}

describe("fetchMe", () => {
  beforeEach(() => {
    cookieStore.clear();
    fetchMock.mockReset();
    process.env.API_INTERNAL_URL = "http://api.test:8000";
    delete process.env.SESSION_COOKIE_NAME;
  });

  afterEach(() => vi.resetModules());

  it("returns null without calling the api when there is no session cookie", async () => {
    const { fetchMe } = await import("./alias");
    expect(await fetchMe()).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("uses the configured session cookie name", async () => {
    process.env.SESSION_COOKIE_NAME = "custom_session";
    cookieStore.set("melos_session", "x");
    const { fetchMe } = await import("./alias");
    expect(await fetchMe()).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each(["en", "es"])("passes the saved language %s through", async (language) => {
    cookieStore.set("melos_session", "tok");
    me({ user_id: "u1", email: "a@example.com", alias: "ana", language });
    const { fetchMe } = await import("./alias");
    expect((await fetchMe())?.language).toBe(language);
  });

  it.each([null, "fr", ""])("treats %j as no saved language", async (language) => {
    cookieStore.set("melos_session", "tok");
    me({ user_id: "u1", email: "a@example.com", alias: "ana", language });
    const { fetchMe } = await import("./alias");
    expect((await fetchMe())?.language).toBeNull();
  });

  it("treats a missing language field as none and keeps the rest of the account", async () => {
    cookieStore.set("melos_session", "tok");
    me({ user_id: "u1", email: "a@example.com", alias: "ana" });
    const { fetchMe } = await import("./alias");
    expect(await fetchMe()).toMatchObject({ user_id: "u1", alias: "ana", language: null });
  });

  it("returns null when the api refuses", async () => {
    cookieStore.set("melos_session", "tok");
    fetchMock.mockResolvedValue(new Response("{}", { status: 401 }));
    const { fetchMe } = await import("./alias");
    expect(await fetchMe()).toBeNull();
  });
});
