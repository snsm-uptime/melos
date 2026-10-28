import { describe, expect, it } from "vitest";

import { signupMessages } from "@/lib/i18n/signup";

describe("signup i18n", () => {
  it("ships EN and ES keys for signup chrome", () => {
    const enKeys = Object.keys(signupMessages.en).sort();
    const esKeys = Object.keys(signupMessages.es).sort();
    expect(esKeys).toEqual(enKeys);
    expect(signupMessages.en.submit).toBeTruthy();
    expect(signupMessages.es.submit).toBeTruthy();
  });
});
