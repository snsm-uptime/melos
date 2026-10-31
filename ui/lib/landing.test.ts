import { describe, expect, it } from "vitest";

import { resolveAuthenticatedLanding } from "./landing";

describe("resolveAuthenticatedLanding", () => {
  it("defaults to Home", () => {
    expect(resolveAuthenticatedLanding()).toBe("/home");
  });

  it("prefers invite deep link for Story 2.4", () => {
    expect(
      resolveAuthenticatedLanding({
        inviteKitchenId: "invite-kitchen",
      }),
    ).toBe("/kitchens/invite-kitchen");
  });
});
