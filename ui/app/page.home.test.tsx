import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const fetchSession = vi.fn();
const resolveServerAuthenticatedLanding = vi.fn();
const requireAlias = vi.fn();
const redirect = vi.fn();

vi.mock("@/lib/session", () => ({
  fetchSession: (...args: unknown[]) => fetchSession(...args),
}));
vi.mock("@/lib/serverLanding", () => ({
  resolveServerAuthenticatedLanding: (...args: unknown[]) => resolveServerAuthenticatedLanding(...args),
}));
const serverLocale = vi.fn();
vi.mock("@/lib/serverLocale", () => ({
  getServerLocale: (...args: unknown[]) => serverLocale(...args),
}));
vi.mock("@/lib/alias", () => ({
  requireAlias: (...args: unknown[]) => requireAlias(...args),
}));
vi.mock("next/navigation", () => ({
  redirect: (...args: unknown[]) => redirect(...args),
}));
vi.mock("@/components/RedirectIfAuthenticated", () => ({
  RedirectIfAuthenticated: () => null,
}));

describe("Home page", () => {
  beforeEach(() => {
    fetchSession.mockReset();
    resolveServerAuthenticatedLanding.mockReset();
    requireAlias.mockReset();
    redirect.mockReset();
    serverLocale.mockReset();
    serverLocale.mockResolvedValue("en");
  });

  afterEach(() => {
    vi.resetModules();
  });

  it("shows product intro copy and sign-up/sign-in CTAs when signed out", async () => {
    fetchSession.mockResolvedValue(null);
    const { default: Home } = await import("./page");

    const markup = renderToStaticMarkup(await Home());

    expect(markup).not.toContain("Stack is up");
    expect(markup).not.toContain("Compose services");
    expect(markup).toMatch(/recipes/i);
    expect(markup).toMatch(/shopping kitchen/i);
    expect(markup).toMatch(/kitchens/i);
    expect(markup).toContain('href="/signup"');
    expect(markup).toContain('href="/sign-in"');
    expect(markup).not.toContain('href="/docs"');
    expect(redirect).not.toHaveBeenCalled();
  });

  it("shows the landing page in Spanish for a Spanish visitor", async () => {
    fetchSession.mockResolvedValue(null);
    serverLocale.mockResolvedValue("es");
    const { default: Home } = await import("./page");

    const markup = renderToStaticMarkup(await Home());

    expect(markup).toContain("Crear una cuenta");
    expect(markup).toContain("Iniciar sesión");
    expect(markup).toContain("Recetas");
    expect(markup).not.toContain("Create an account");
    expect(markup).not.toContain("Sign in");
  });

  it("redirects to the resolved landing destination when signed in", async () => {
    fetchSession.mockResolvedValue({ userId: "u1" });
    resolveServerAuthenticatedLanding.mockResolvedValue("/kitchens/123");
    requireAlias.mockResolvedValue(undefined);
    const { default: Home } = await import("./page");

    await Home();

    expect(resolveServerAuthenticatedLanding).toHaveBeenCalled();
    expect(requireAlias).toHaveBeenCalledWith("/kitchens/123");
    expect(redirect).toHaveBeenCalledWith("/kitchens/123");
  });
});
