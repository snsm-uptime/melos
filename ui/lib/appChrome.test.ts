import { describe, expect, it } from "vitest";

import {
  panelEntryFromPath,
  showsAppChrome,
  showsFloatingLanguageSwitch,
  showsLanguageSwitch,
} from "./appChrome";

describe("showsAppChrome", () => {
  it("keeps the side panel on authenticated product surfaces", () => {
    expect(showsAppChrome("/home")).toBe(true);
    expect(showsAppChrome("/kitchens/abc")).toBe(true);
    expect(showsAppChrome("/notebooks")).toBe(true);
    expect(showsAppChrome("/notebooks/nb-1")).toBe(true);
    expect(showsAppChrome("/recipes/r1")).toBe(true);
    expect(showsAppChrome("/recipes/r1/edit")).toBe(true);
  });

  it("hides the side panel on auth, setup and removed finance routes", () => {
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

describe("panelEntryFromPath", () => {
  it("marks nothing on /home and the kitchen under any kitchen path", () => {
    expect(panelEntryFromPath("/home")).toBeUndefined();
    expect(panelEntryFromPath("/kitchens/k1/cart")).toBe("kitchen:k1");
  });

  it("marks another kitchen, also while the default is unknown", () => {
    expect(panelEntryFromPath("/kitchens/k2/cart")).toBe("kitchen:k2");
    expect(panelEntryFromPath("/kitchens/k2")).toBe("kitchen:k2");
  });

  it("marks Notebooks on notebooks and on a recipe's pages", () => {
    expect(panelEntryFromPath("/notebooks")).toBe("notebooks");
    expect(panelEntryFromPath("/notebooks/nb-1")).toBe("notebooks");
    expect(panelEntryFromPath("/recipes/r1/edit")).toBe("notebooks");
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
