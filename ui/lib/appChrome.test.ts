import { describe, expect, it } from "vitest";

import { showsAppChrome, tabKeyFromPath } from "./appChrome";

describe("showsAppChrome", () => {
  it("keeps the tab bar on authenticated product surfaces", () => {
    expect(showsAppChrome("/home")).toBe(true);
    expect(showsAppChrome("/kitchens/abc")).toBe(true);
    expect(showsAppChrome("/account")).toBe(true);
    expect(showsAppChrome("/notebooks")).toBe(true);
    expect(showsAppChrome("/notebooks/nb-1")).toBe(true);
  });

  it("hides the tab bar on auth, setup and removed finance routes", () => {
    expect(showsAppChrome("/")).toBe(false);
    expect(showsAppChrome("/sign-in")).toBe(false);
    expect(showsAppChrome("/signup")).toBe(false);
    expect(showsAppChrome("/alias")).toBe(false);
    expect(showsAppChrome("/invites/accept")).toBe(false);
    expect(showsAppChrome("/forgot-password")).toBe(false);
    expect(showsAppChrome("/cards")).toBe(false);
    expect(showsAppChrome("/budgets")).toBe(false);
    expect(showsAppChrome("/upload")).toBe(false);
  });
});

describe("tabKeyFromPath", () => {
  it("marks Home active on home and kitchen detail", () => {
    expect(tabKeyFromPath("/home")).toBe("home");
    expect(tabKeyFromPath("/kitchens/abc")).toBe("home");
  });

  it("marks Account from its route", () => {
    expect(tabKeyFromPath("/account")).toBe("account");
  });

  it("marks Notebook on the tab and its sub-paths", () => {
    expect(tabKeyFromPath("/notebooks")).toBe("notebook");
    expect(tabKeyFromPath("/notebooks/nb-1")).toBe("notebook");
  });
});
