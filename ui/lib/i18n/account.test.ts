import { describe, expect, it } from "vitest";

import { accountMessages } from "./account";

describe("account i18n", () => {
  it("ships Account chrome keys in EN and ES", () => {
    const required = [
      "language",
      "theme",
      "en",
      "es",
      "light",
      "dark",
      "system",
      "signOut",
      "passwordReset",
      "loading",
      "saveLanguageFailed",
      "saveThemeFailed",
    ] as const;

    for (const key of required) {
      expect(accountMessages.en[key].length).toBeGreaterThan(0);
      expect(accountMessages.es[key].length).toBeGreaterThan(0);
    }
  });

});
