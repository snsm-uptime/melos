import { describe, expect, it } from "vitest";

import {
  showsAppChrome,
  showsFloatingLanguageSwitch,
  showsLanguageSwitch,
  tabKeyFromPath,
} from "./appChrome";

describe("showsAppChrome", () => {
  it("keeps the tab bar on authenticated product surfaces", () => {
    expect(showsAppChrome("/home")).toBe(true);
    expect(showsAppChrome("/kitchens/abc")).toBe(true);
    expect(showsAppChrome("/account")).toBe(true);
    expect(showsAppChrome("/notebooks")).toBe(true);
    expect(showsAppChrome("/notebooks/nb-1")).toBe(true);
    expect(showsAppChrome("/recipes/r1")).toBe(true);
    expect(showsAppChrome("/recipes/r1/edit")).toBe(true);
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

  it("marks Notebook on a recipe's detail and edit pages", () => {
    expect(tabKeyFromPath("/recipes/r1")).toBe("notebook");
    expect(tabKeyFromPath("/recipes/r1/edit")).toBe("notebook");
  });
});

describe("showsLanguageSwitch (spec 063)", () => {
  it("is on for the signed-out screens", () => {
    for (const path of [
      "/",
      "/sign-in",
      "/signup",
      "/sign-up",
      "/forgot-password",
      "/reset-password",
      "/verify",
      "/invites/accept",
    ]) {
      expect(showsLanguageSwitch(path)).toBe(true);
    }
  });

  it("is off everywhere else", () => {
    for (const path of ["/home", "/account", "/alias", "/notebooks/n1", "/recipes/r1", "/invites", "/signing"]) {
      expect(showsLanguageSwitch(path)).toBe(false);
    }
  });
});

describe("showsFloatingLanguageSwitch", () => {
  it("floats on the signed-out screens except /sign-in, which has the switch in its card", () => {
    for (const path of ["/", "/signup", "/sign-up", "/forgot-password", "/reset-password", "/verify", "/invites/accept"]) {
      expect(showsFloatingLanguageSwitch(path)).toBe(true);
    }
    expect(showsFloatingLanguageSwitch("/sign-in")).toBe(false);
    expect(showsFloatingLanguageSwitch("/home")).toBe(false);
  });
});
