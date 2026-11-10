import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { availableFeatures, groupsInOrder, plannedFeatures } from "@/lib/featureInventory";
import { landingMessages, type DemoId } from "@/lib/i18n/landing";

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
// The demo frame is a client component; here it shows what it was given, so the page renders on
// the server alone.
vi.mock("@/components/LandingTour/DemoFrame", () => ({
  DemoFrame: ({ title, description, children }: { title: string; description: string; children: ReactNode }) => (
    <figure data-demo-title={title}>
      <figcaption>{description}</figcaption>
      {children}
    </figure>
  ),
}));

const GROUP_IDS = ["capture", "notebooks", "together", "shop", "ingredients", "home"];

/** Text as renderToStaticMarkup writes it. */
function escaped(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");
}

/** The markup of `<section id="…">`, up to its closing tag. */
function section(markup: string, id: string): string {
  const start = markup.indexOf(`<section id="${id}"`);
  if (start < 0) return "";
  return markup.slice(start, markup.indexOf("</section>", start));
}

async function renderHome(locale: "en" | "es" = "en"): Promise<string> {
  fetchSession.mockResolvedValue(null);
  serverLocale.mockResolvedValue(locale);
  const { default: Home } = await import("./page");
  return renderToStaticMarkup(await Home());
}

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

  it("puts the decorative cauldron before the app name", async () => {
    const markup = await renderHome();

    const heading = markup.slice(markup.indexOf("<h1"), markup.indexOf("</h1>"));
    expect(heading).toContain('aria-hidden="true"');
    expect(heading.indexOf("<svg")).toBeLessThan(heading.indexOf("Melos"));
  });

  it("shows the tour regions in order: hero, six groups, coming soon, closing call to action", async () => {
    const markup = await renderHome();

    expect(markup.match(/<h1[\s>]/g)).toHaveLength(1);
    const positions = [...GROUP_IDS, "coming-soon"].map((id) => markup.indexOf(`<section id="${id}"`));
    for (const position of positions) expect(position).toBeGreaterThan(-1);
    expect(positions).toEqual([...positions].sort((a, b) => a - b));

    // The account buttons sit in the hero and again after the coming-soon strip.
    const afterStrip = markup.slice(positions.at(-1)!);
    expect(markup.indexOf('href="/signup"')).toBeLessThan(positions[0]);
    expect(markup.indexOf('href="/sign-in"')).toBeLessThan(positions[0]);
    expect(afterStrip).toContain('href="/signup"');
    expect(afterStrip).toContain('href="/sign-in"');
    expect(markup).not.toContain('href="/docs"');
    expect(redirect).not.toHaveBeenCalled();
  });

  it("lists each available feature inside its own group section, and planned ones only in the strip", async () => {
    const markup = await renderHome();

    for (const group of groupsInOrder()) {
      const html = section(markup, group.id);
      expect(html, group.id).toContain(escaped(group.title.en));
      for (const feature of availableFeatures(group.id)) {
        expect(html, feature.id).toContain(escaped(feature.name.en));
      }
      for (const feature of plannedFeatures()) {
        expect(html, feature.id).not.toContain(escaped(feature.name.en));
      }
    }
    const strip = section(markup, "coming-soon");
    for (const feature of plannedFeatures()) expect(strip, feature.id).toContain(escaped(feature.name.en));
  });

  it("shows the overview demo in the hero, then one demo per group, in order", async () => {
    const markup = await renderHome();
    const demo = landingMessages.en.demo;

    const titles = [...markup.matchAll(/data-demo-title="([^"]*)"/g)].map((m) => m[1]);
    expect(titles).toEqual(
      ["overview", ...GROUP_IDS].map((id) => escaped(demo[id as DemoId].title)),
    );
    expect(markup.indexOf("data-demo-title")).toBeLessThan(markup.indexOf('<section id="capture"'));
    for (const id of GROUP_IDS) {
      const key = id as "capture";
      expect(section(markup, id), id).toContain(escaped(demo[key].description));
    }
  });

  it("says shopping list, never shopping kitchen (FR-016)", async () => {
    const en = await renderHome("en");
    expect(en).toContain("shopping list");
    expect(en).not.toMatch(/shopping kitchen/i);

    vi.resetModules();
    const es = await renderHome("es");
    expect(es).toContain("lista de compras");
    expect(es).not.toMatch(/cocina de compras/i);
  });

  it("shows the landing page in Spanish for a Spanish visitor", async () => {
    const markup = await renderHome("es");

    expect(markup).toContain("Crear una cuenta");
    expect(markup).toContain("Iniciar sesión");
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
