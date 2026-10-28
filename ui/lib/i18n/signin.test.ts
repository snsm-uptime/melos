import { describe, expect, it } from "vitest";

import { signInMessages } from "./signin";

describe("sign-in i18n", () => {
  it("ships generic credential error in EN and ES", () => {
    expect(signInMessages.en.errorGeneric.toLowerCase()).toContain("invalid");
    expect(signInMessages.es.errorGeneric.length).toBeGreaterThan(10);
  });
});
