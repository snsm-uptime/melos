import { describe, expect, it } from "vitest";

import { DEFAULT_LOCALE, isLocale, resolveLocale } from "./locale";

describe("resolveLocale and isLocale (spec 063)", () => {
  it("keeps English and Spanish", () => {
    expect(resolveLocale("en")).toBe("en");
    expect(resolveLocale("es")).toBe("es");
  });

  it.each([null, undefined, "", "fr", "EN", "es-CR", "en "])("falls back to Spanish for %j", (raw) => {
    expect(resolveLocale(raw)).toBe("es");
    expect(DEFAULT_LOCALE).toBe("es");
  });

  it("isLocale accepts only en and es", () => {
    expect(isLocale("en")).toBe(true);
    expect(isLocale("es")).toBe(true);
    expect(isLocale("fr")).toBe(false);
    expect(isLocale(null)).toBe(false);
    expect(isLocale(1)).toBe(false);
  });
});
