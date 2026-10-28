import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { localeMock } = vi.hoisted(() => ({ localeMock: vi.fn() }));

vi.mock("next/font/google", () => ({
  Manrope: () => ({ variable: "font-ui" }),
  Petrona: () => ({ variable: "font-brand" }),
}));
vi.mock("@/lib/serverLocale", () => ({ getServerLocale: localeMock }));
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

import RootLayout from "./layout";

async function render(): Promise<string> {
  return renderToStaticMarkup(await RootLayout({ children: <p>content</p> }));
}

describe("RootLayout", () => {
  beforeEach(() => localeMock.mockReset());

  it.each(["es", "en"])("declares the server locale %s and hands it to the provider", async (locale) => {
    localeMock.mockResolvedValue(locale);
    const html = await render();
    expect(html).toContain(`lang="${locale}"`);
    expect(html).toContain(`data-initial-locale="${locale}"`);
  });

  it("no longer reads a remembered language in the boot script", async () => {
    localeMock.mockResolvedValue("es");
    const html = await render();
    expect(html).not.toContain("melos_lang_cache");
    expect(html).toContain("melos_theme_cache");
  });
});
