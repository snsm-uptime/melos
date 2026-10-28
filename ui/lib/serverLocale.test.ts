import { beforeEach, describe, expect, it, vi } from "vitest";

const { fetchMeMock, cookieStore } = vi.hoisted(() => ({
  fetchMeMock: vi.fn(),
  cookieStore: new Map<string, string>(),
}));

vi.mock("@/lib/alias", () => ({ fetchMe: fetchMeMock }));
vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => (cookieStore.has(name) ? { name, value: cookieStore.get(name) } : undefined),
  }),
}));

const account = (language: string | null) => ({
  user_id: "u1",
  email: "a@example.com",
  alias: "ana",
  photo_base64: null,
  language,
});

describe("getServerLocale", () => {
  beforeEach(() => {
    fetchMeMock.mockReset();
    cookieStore.clear();
  });

  it("uses the saved language of a signed-in account", async () => {
    const { getServerLocale } = await import("./serverLocale");
    fetchMeMock.mockResolvedValue(account("en"));
    expect(await getServerLocale()).toBe("en");
    fetchMeMock.mockResolvedValue(account("es"));
    expect(await getServerLocale()).toBe("es");
  });

  it("is Spanish for an account with no saved language or a bad value", async () => {
    const { getServerLocale } = await import("./serverLocale");
    fetchMeMock.mockResolvedValue(account(null));
    expect(await getServerLocale()).toBe("es");
    fetchMeMock.mockResolvedValue(account("fr"));
    expect(await getServerLocale()).toBe("es");
  });

  it("ignores the signed-out pick when an account is signed in", async () => {
    const { getServerLocale } = await import("./serverLocale");
    cookieStore.set("melos_lang", "en");
    fetchMeMock.mockResolvedValue(account(null));
    expect(await getServerLocale()).toBe("es");
    cookieStore.set("melos_lang", "es");
    fetchMeMock.mockResolvedValue(account("en"));
    expect(await getServerLocale()).toBe("en");
  });

  it("uses the signed-out pick when there is no account", async () => {
    const { getServerLocale } = await import("./serverLocale");
    fetchMeMock.mockResolvedValue(null);
    cookieStore.set("melos_lang", "en");
    expect(await getServerLocale()).toBe("en");
  });

  it("is Spanish with no account and no pick, or a bad pick", async () => {
    const { getServerLocale } = await import("./serverLocale");
    fetchMeMock.mockResolvedValue(null);
    expect(await getServerLocale()).toBe("es");
    cookieStore.set("melos_lang", "fr");
    expect(await getServerLocale()).toBe("es");
  });

  it("does not read the old cache cookie", async () => {
    const { getServerLocale } = await import("./serverLocale");
    fetchMeMock.mockResolvedValue(null);
    cookieStore.set("melos_lang_cache", "en");
    expect(await getServerLocale()).toBe("es");
  });
});
