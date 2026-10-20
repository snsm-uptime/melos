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
        lastOpenedKitchenId: "old",
        lastOpenedStillAccessible: true,
      }),
    ).toBe("/kitchens/invite-kitchen");
  });

  it("uses remembered kitchen only when still accessible via ACL", () => {
    expect(
      resolveAuthenticatedLanding({
        lastOpenedKitchenId: "abc",
        lastOpenedStillAccessible: true,
      }),
    ).toBe("/kitchens/abc");
    expect(
      resolveAuthenticatedLanding({
        lastOpenedKitchenId: "abc",
        lastOpenedStillAccessible: false,
      }),
    ).toBe("/home");
  });
});
