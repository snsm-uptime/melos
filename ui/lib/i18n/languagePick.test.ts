/** @vitest-environment jsdom */

import { afterEach, describe, expect, it, vi } from "vitest";

import { clearLanguagePick, readLanguagePick, writeLanguagePick } from "./languagePick";

afterEach(() => {
  clearLanguagePick();
  vi.restoreAllMocks();
});

describe("language pick cookie", () => {
  it("writes and reads a pick", () => {
    expect(readLanguagePick()).toBeNull();
    writeLanguagePick("en");
    expect(readLanguagePick()).toBe("en");
    writeLanguagePick("es");
    expect(readLanguagePick()).toBe("es");
  });

  it("reads null for a value that is not English or Spanish", () => {
    document.cookie = "melos_lang=fr; Path=/";
    expect(readLanguagePick()).toBeNull();
  });

  it("is not confused by other cookies", () => {
    document.cookie = "other=1; Path=/";
    writeLanguagePick("en");
    document.cookie = "another=2; Path=/";
    expect(readLanguagePick()).toBe("en");
    document.cookie = "melos_lang_cache=es; Path=/";
    clearLanguagePick();
    expect(readLanguagePick()).toBeNull();
  });

  it("clears the pick", () => {
    writeLanguagePick("en");
    clearLanguagePick();
    expect(readLanguagePick()).toBeNull();
  });

  it("writes a session cookie: no max-age and no expires", () => {
    const setter = vi.spyOn(document, "cookie", "set");
    writeLanguagePick("en");
    const written = String(setter.mock.calls[0][0]).toLowerCase();
    expect(written).toContain("melos_lang=en");
    expect(written).toContain("path=/");
    expect(written).toContain("samesite=lax");
    expect(written).not.toContain("max-age");
    expect(written).not.toContain("expires");
  });

  it("never throws when cookies are blocked", () => {
    vi.spyOn(document, "cookie", "set").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(document, "cookie", "get").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(() => writeLanguagePick("en")).not.toThrow();
    expect(() => clearLanguagePick()).not.toThrow();
    expect(readLanguagePick()).toBeNull();
  });
});
