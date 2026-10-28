/** @vitest-environment jsdom */

import { act, useEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearLanguagePick, writeLanguagePick } from "@/lib/i18n/languagePick";

import { PreferencesProvider, usePreferences } from "./PreferencesProvider";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

type Prefs = ReturnType<typeof usePreferences>;
const seen: { latest: Prefs | null; renders: string[] } = { latest: null, renders: [] };

function Probe() {
  const prefs = usePreferences();
  // Recorded after each commit, not during render, so the sequence is what the screen showed.
  useEffect(() => {
    seen.latest = prefs;
    seen.renders.push(prefs.locale);
  });
  return <span data-locale={prefs.locale}>{prefs.locale}</span>;
}

type Reply = { status: number; body?: unknown };
let me: Reply;
let patch: Reply;
let calls: { url: string; method: string; body: unknown }[];

function stubFetch() {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      calls.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) : undefined });
      const reply = method === "PATCH" ? patch : me;
      return new Response(JSON.stringify(reply.body ?? {}), { status: reply.status });
    }),
  );
}

const account = (language: string | null) => ({
  status: 200,
  body: { user_id: "u1", email: "a@example.com", language, theme: "system", alias: "ana", photo_base64: null },
});

describe("PreferencesProvider language (spec 063)", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    refresh.mockReset();
    seen.renders.length = 0;
    me = account("es");
    patch = account("en");
    stubFetch();
    clearLanguagePick();
    localStorage.clear();
    document.documentElement.lang = "";
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
    clearLanguagePick();
  });

  async function render(initialLocale?: "en" | "es") {
    await act(async () => {
      root.render(
        <PreferencesProvider initialLocale={initialLocale}>
          <Probe />
        </PreferencesProvider>,
      );
    });
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 5));
    });
  }

  const shown = () => container.querySelector("span")?.getAttribute("data-locale");

  it("starts from the server's language, with no read of a remembered value", async () => {
    localStorage.setItem("melos_lang_cache", "en");
    me = { status: 401 };
    await act(async () => {
      root.render(
        <PreferencesProvider initialLocale="es">
          <Probe />
        </PreferencesProvider>,
      );
    });
    expect(seen.renders[0]).toBe("es");
    expect(seen.renders).not.toContain("en");
  });

  it("starts in Spanish when no initial language is given", async () => {
    me = { status: 401 };
    await render();
    expect(seen.renders[0]).toBe("es");
  });

  it("takes the saved language of a signed-in account", async () => {
    me = account("en");
    await render("es");
    expect(shown()).toBe("en");
    expect(document.documentElement.lang).toBe("en");
  });

  it("is Spanish for an account with no saved language", async () => {
    me = account(null);
    await render("en");
    expect(shown()).toBe("es");
  });

  it("uses the signed-out pick when signed out, else Spanish", async () => {
    me = { status: 401 };
    writeLanguagePick("en");
    await render("en");
    expect(shown()).toBe("en");
    act(() => root.unmount());
    root = createRoot(container);
    clearLanguagePick();
    await render("en");
    expect(shown()).toBe("es");
  });

  it("is not changed by the browser's language", async () => {
    vi.spyOn(navigator, "language", "get").mockReturnValue("en-US");
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["en-US", "en"]);
    me = { status: 401 };
    await render();
    expect(shown()).toBe("es");
  });

  it("saves a signed-in choice with one PATCH, switches at once and refreshes the server pages", async () => {
    me = account("es");
    await render("es");
    calls.length = 0;
    await act(async () => {
      await seen.latest!.setLanguage("en");
    });
    const patches = calls.filter((call) => call.method === "PATCH");
    expect(patches).toHaveLength(1);
    expect(patches[0].url).toBe("/api/auth/me");
    expect(patches[0].body).toEqual({ language: "en" });
    expect(shown()).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(seen.latest?.me?.language).toBe("en");
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("keeps the language and rejects when the save fails", async () => {
    me = account("es");
    await render("es");
    patch = { status: 500 };
    await act(async () => {
      await expect(seen.latest!.setLanguage("en")).rejects.toThrow();
    });
    expect(shown()).toBe("es");
    expect(document.documentElement.lang).not.toBe("en");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("signed out, writes the pick cookie, switches at once and sends nothing", async () => {
    me = { status: 401 };
    await render("es");
    calls.length = 0;
    await act(async () => {
      await seen.latest!.setLanguage("en");
    });
    expect(calls).toEqual([]);
    expect(document.cookie).toContain("melos_lang=en");
    expect(shown()).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("never writes the language to local storage", async () => {
    me = account("en");
    await render("es");
    await act(async () => {
      await seen.latest!.setLanguage("es");
    });
    expect(localStorage.getItem("melos_lang_cache")).toBeNull();
  });
});
