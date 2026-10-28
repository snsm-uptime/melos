import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * The page's language end to end through the real `getServerLocale` (spec 063 FR-011, FR-012,
 * FR-018): only the account lookup and the cookies are faked.
 */
const { fetchMeMock, cookieStore } = vi.hoisted(() => ({
  fetchMeMock: vi.fn(),
  cookieStore: new Map<string, string>(),
}));

vi.mock("next/font/google", () => ({
  Manrope: () => ({ variable: "font-ui" }),
  Petrona: () => ({ variable: "font-brand" }),
}));
vi.mock("@/lib/alias", () => ({ fetchMe: fetchMeMock }));
vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => (cookieStore.has(name) ? { name, value: cookieStore.get(name) } : undefined),
  }),
}));
vi.mock("@/components/AppShell", () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/components/PreferencesProvider", async () => {
  const actual = await vi.importActual<typeof import("@/components/PreferencesProvider")>(
    "@/components/PreferencesProvider",
  );
  return {
    ...actual,
    PreferencesProvider: ({
      children,
      initialLocale,
    }: {
      children: React.ReactNode;
      initialLocale: string;
    }) => <div data-initial-locale={initialLocale}>{children}</div>,
  };
});

const account = (language: string | null) => ({
  user_id: "u1",
  email: "a@example.com",
  alias: "ana",
  photo_base64: null,
  language,
});

async function page(): Promise<string> {
  vi.resetModules();
  const { default: RootLayout } = await import("./layout");
  return renderToStaticMarkup(await RootLayout({ children: <p>x</p> }));
}

describe("the page language, from the account or the pick", () => {
  beforeEach(() => {
    fetchMeMock.mockReset();
    cookieStore.clear();
  });

  it("a signed-in English account declares English even with a Spanish pick left in a cookie", async () => {
    fetchMeMock.mockResolvedValue(account("en"));
    cookieStore.set("melos_lang", "es");
    const html = await page();
    expect(html).toContain('lang="en"');
    expect(html).toContain('data-initial-locale="en"');
  });

  it("a signed-in account with no saved language declares Spanish, whatever the pick says", async () => {
    fetchMeMock.mockResolvedValue(account(null));
    cookieStore.set("melos_lang", "en");
    expect(await page()).toContain('lang="es"');
  });

  it("a visitor who picked English declares English from the first byte", async () => {
    fetchMeMock.mockResolvedValue(null);
    cookieStore.set("melos_lang", "en");
    const html = await page();
    expect(html).toContain('lang="en"');
    expect(html).toContain('data-initial-locale="en"');
  });

  it("a visitor with no pick declares Spanish", async () => {
    fetchMeMock.mockResolvedValue(null);
    const html = await page();
    expect(html).toContain('lang="es"');
    expect(html).toContain('data-initial-locale="es"');
  });
});
