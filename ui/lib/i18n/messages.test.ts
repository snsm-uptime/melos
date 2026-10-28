import { describe, expect, it } from "vitest";

import { messagesFor } from "./messages";

const set = {
  en: { hello: "Hello", bye: "Bye", count: (n: number) => `${n} items` },
  es: { hello: "Hola", count: (n: number) => `${n} elementos` },
};

describe("messagesFor", () => {
  it("returns Spanish where it exists", () => {
    const t = messagesFor(set, "es");
    expect(t.hello).toBe("Hola");
    expect(t.count(2)).toBe("2 elementos");
  });

  it("falls back to English for a message missing in Spanish", () => {
    expect(messagesFor(set, "es").bye).toBe("Bye");
  });

  it("returns English for English", () => {
    const t = messagesFor(set, "en");
    expect(t.hello).toBe("Hello");
    expect(t.count(2)).toBe("2 items");
  });
});
