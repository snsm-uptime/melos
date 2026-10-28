import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * The server-built pages show the language `getServerLocale()` gives them, not a guess from the
 * browser (spec 063 US4). Everything else a page needs is faked.
 */
const { localeMock } = vi.hoisted(() => ({ localeMock: vi.fn() }));

vi.mock("@/lib/serverLocale", () => ({ getServerLocale: localeMock }));
vi.mock("@/lib/session", () => ({ fetchSession: async () => null }));
vi.mock("@/lib/serverLanding", () => ({ resolveServerAuthenticatedLanding: async () => "/home" }));
vi.mock("@/lib/alias", () => ({ requireAlias: vi.fn(), fetchMe: async () => null }));
vi.mock("next/navigation", () => ({ redirect: vi.fn(), useRouter: () => ({}) }));
vi.mock("@/components/RedirectIfAuthenticated", () => ({ RedirectIfAuthenticated: () => null }));
vi.mock("@/app/sign-in/SignInChrome", () => ({ SignInChrome: () => null }));
vi.mock("@/app/sign-in/SignInForm", () => ({ SignInForm: () => <form data-form="sign-in" /> }));
vi.mock("@/components/SignedOutLanguageSwitch", () => ({
  SignedOutLanguageSwitch: ({ placement }: { placement?: string }) => <div data-switch={placement} />,
}));
vi.mock("@/app/signup/SignupForm", () => ({ SignupForm: () => null }));
vi.mock("@/app/forgot-password/ForgotPasswordForm", () => ({ ForgotPasswordForm: () => null }));
vi.mock("@/app/verify/VerifyForm", () => ({ VerifyForm: () => null }));

async function render(load: () => Promise<{ default: (props: never) => Promise<React.ReactNode> }>, props: object = {}) {
  const { default: Page } = await load();
  return renderToStaticMarkup(await Page(props as never));
}

const pages: [string, () => Promise<{ default: (props: never) => Promise<React.ReactNode> }>, object, string, string][] = [
  ["sign-in", () => import("@/app/sign-in/page") as never, { searchParams: Promise.resolve({}) }, "Iniciar sesión", "Sign in"],
  ["signup", () => import("@/app/signup/page") as never, { searchParams: Promise.resolve({}) }, "Crear cuenta", "Create account"],
  ["forgot-password", () => import("@/app/forgot-password/page") as never, {}, "Olvidé mi contraseña", "Forgot password"],
  ["landing", () => import("@/app/page") as never, {}, "Crear una cuenta", "Create an account"],
];

describe("server-built pages follow getServerLocale()", () => {
  beforeEach(() => localeMock.mockReset());

  it.each(pages)("%s in Spanish and in English", async (_name, load, props, spanish, english) => {
    localeMock.mockResolvedValue("es");
    const es = await render(load, props);
    expect(es).toContain(spanish);
    expect(es).not.toContain(english);
    localeMock.mockResolvedValue("en");
    const en = await render(load, props);
    expect(en).toContain(english);
    expect(en).not.toContain(spanish);
  });

  it("sign-in carries the language switch inside its card, after the form (which ends with the sign-up link)", async () => {
    localeMock.mockResolvedValue("es");
    const html = await render(() => import("@/app/sign-in/page") as never, {
      searchParams: Promise.resolve({}),
    });
    const form = html.indexOf('data-form="sign-in"');
    const languageSwitch = html.indexOf('data-switch="inline"');
    expect(form).toBeGreaterThan(-1);
    expect(languageSwitch).toBeGreaterThan(form);
    // Inside the card, not floating: one switch, and before the card closes.
    expect(html.match(/data-switch=/g)).toHaveLength(1);
  });
});
