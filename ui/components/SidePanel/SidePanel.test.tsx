/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
const refresh = vi.fn();
let pathname = "/recipes/r1";
vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ push, refresh }),
}));

let locale: "en" | "es" = "en";
let photo: string | null = null;
vi.mock("@/components/PreferencesProvider", () => ({
  usePreferences: () => ({
    locale,
    me: { alias: "ana", user_id: "u1", photo_base64: photo },
    theme: "system",
    ready: true,
    setTheme: vi.fn(),
    setLanguage: vi.fn(),
    refresh: vi.fn(),
  }),
  clearPrefsCache: () => {},
}));

const fetchKitchens = vi.fn();
const createKitchen = vi.fn();
vi.mock("@/app/kitchens/kitchensClient", async (original) => ({
  ...(await original<typeof import("@/app/kitchens/kitchensClient")>()),
  fetchKitchens: (...args: unknown[]) => fetchKitchens(...args),
  createKitchen: (...args: unknown[]) => createKitchen(...args),
}));

const fetchSidePanel = vi.fn();
const setDefaultKitchen = vi.fn();
vi.mock("@/lib/sidePanelClient", async (original) => ({
  ...(await original<typeof import("@/lib/sidePanelClient")>()),
  fetchSidePanel: () => fetchSidePanel(),
  setDefaultKitchen: (...args: unknown[]) => setDefaultKitchen(...args),
}));

const signOut = vi.fn<(target: string) => Promise<void>>(() => new Promise<void>(() => {}));
vi.mock("@/lib/signOut", () => ({ signOut: (target: string) => signOut(target) }));

import {
  replaceMembershipKitchens,
  resetMembershipKitchensStore,
} from "@/app/kitchens/membershipKitchensStore";
import { requestSidePanelRefresh } from "@/lib/sidePanelClient";
import { SidePanel } from "./SidePanel";
import { SIDE_PANEL_KEY } from "./useSidePanelState";

const kitchen = (id: string, name: string) => ({ id, name, owner_id: "u1", role: "owner" });
const KITCHENS = [kitchen("k1", "Mine"), kitchen("k3", "zoo"), kitchen("k2", "Apple")];

describe("SidePanel", () => {
  let host: HTMLDivElement;
  let root: Root;
  const onDrawerClose = vi.fn();

  function stubKitchens(active = KITCHENS, archived = [kitchen("k9", "Old")]) {
    fetchKitchens.mockImplementation(async (_messages, options) => {
      const list = options?.archived ? archived : active;
      if (!options?.archived) replaceMembershipKitchens(list);
      return { ok: true, kitchens: list };
    });
  }

  async function render(drawerOpen = false) {
    await act(async () => {
      root.render(<SidePanel drawerOpen={drawerOpen} onDrawerClose={onDrawerClose} />);
    });
  }

  const nav = () => host.querySelector("nav") as HTMLElement;
  const link = (label: string) => host.querySelector(`a[aria-label="${label}"]`) as HTMLElement;
  const button = (label: string) =>
    host.querySelector(`button[aria-label="${label}"]`) as HTMLButtonElement;
  const names = () =>
    Array.from(host.querySelectorAll("nav a, nav button"))
      .filter((el) => !el.closest("[inert]"))
      .map((el) => el.getAttribute("aria-label"))
      .filter((label) => label !== "Close menu" && label !== "Open menu");

  beforeEach(() => {
    vi.clearAllMocks();
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    window.localStorage.clear();
    pathname = "/recipes/r1";
    locale = "en";
    photo = null;
    fetchSidePanel.mockResolvedValue({ default_kitchen_id: "k1", recipes_added: 5, notebooks: 2 });
    stubKitchens();
    host = document.createElement("div");
    document.body.appendChild(host);
    root = createRoot(host);
  });

  afterEach(() => {
    act(() => root.unmount());
    host.remove();
    resetMembershipKitchensStore();
  });

  it("keeps the entry order, with the default first and the others A to Z", async () => {
    await render();
    expect(names()).toEqual([
      "Notebooks",
      "Show archived kitchens",
      "Create kitchen",
      "Mine",
      "Apple",
      "Set as default",
      "zoo",
      "Set as default",
      "Settings",
      "Log out",
    ]);
  });

  it("has no Home entry", async () => {
    await render();
    expect(link("Home")).toBeNull();
  });

  it("shows one kitchen as the default", async () => {
    stubKitchens([KITCHENS[0]]);
    await render();
    expect(link("Mine")).toBeTruthy();
    expect(button("Set as default")).toBeNull();
  });

  it("marks the default with a filled star and moves a newly starred kitchen up", async () => {
    await render();
    const star = host.querySelector('[role="img"][aria-label="Default kitchen"] path');
    expect(star?.getAttribute("fill")).toBe("currentColor");
    setDefaultKitchen.mockResolvedValue({ default_kitchen_id: "k3", recipes_added: 5, notebooks: 2 });
    const zooStar = link("zoo").closest("li")?.querySelector("button") as HTMLButtonElement;
    await act(async () => zooStar.click());
    expect(setDefaultKitchen).toHaveBeenCalledWith("k3");
    expect(names()[3]).toBe("zoo");
    expect(refresh).toHaveBeenCalled();
  });

  it("keeps the default and says so when starring fails", async () => {
    await render();
    setDefaultKitchen.mockResolvedValue(null);
    await act(async () => button("Set as default").click());
    expect(names()[3]).toBe("Mine");
    expect(host.querySelector('[role="alert"]')).toBeTruthy();
  });

  it("shows no stars on archived kitchens", async () => {
    await render();
    await act(async () => button("Show archived kitchens").click());
    expect(button("Set as default")).toBeNull();
  });

  it("widens a closed panel to show settings, and resets the password from there", async () => {
    await render();
    await act(async () => button("Settings").click());
    expect(window.localStorage.getItem(SIDE_PANEL_KEY)).toBe("true");
    expect(button("Settings").getAttribute("aria-expanded")).toBe("true");
    const reset = Array.from(host.querySelectorAll("button")).find(
      (el) => el.textContent === "Password reset",
    );
    await act(async () => reset?.click());
    expect(signOut).toHaveBeenCalledWith("/forgot-password");
  });

  it("offers photo edits on the avatar, removal only with a photo", async () => {
    await render();
    expect(host.querySelector('input[type="file"]')).toBeTruthy();
    expect(button("Remove photo")).toBeNull();
    photo = "data:image/png;base64,AA";
    await act(async () => requestSidePanelRefresh());
    await render();
    expect(button("Remove photo")).toBeTruthy();
  });

  it("links each kitchen", async () => {
    await render();
    expect(link("zoo").getAttribute("href")).toBe("/kitchens/k3");
  });

  it("marks Notebooks on a recipe page", async () => {
    await render();
    expect(link("Notebooks").getAttribute("aria-current")).toBe("page");
  });

  it("marks the default kitchen like any other", async () => {
    pathname = "/kitchens/k1/cart";
    await render();
    expect(link("Mine").getAttribute("aria-current")).toBe("page");
  });

  it("refetches on a page change and on request", async () => {
    await render();
    expect(fetchSidePanel).toHaveBeenCalledTimes(1);
    pathname = "/notebooks";
    await render();
    expect(fetchSidePanel).toHaveBeenCalledTimes(2);
    await act(async () => requestSidePanelRefresh());
    expect(fetchSidePanel).toHaveBeenCalledTimes(3);
  });

  it("hides labels from `md` up when closed, keeping accessible names", async () => {
    await render();
    expect(nav().className).toContain("md:w-(--panel-width-closed)");
    expect(link("Apple").querySelector("span:last-child")?.className).toContain("md:hidden");
    expect(link("Apple").getAttribute("aria-label")).toBe("Apple");
    expect(host.querySelector('[data-side-panel="identity"]')?.className).toContain("md:hidden");
  });

  it("toggles with the control and remembers it", async () => {
    await render();
    await act(async () => button("Open menu").click());
    expect(window.localStorage.getItem(SIDE_PANEL_KEY)).toBe("true");
    expect(nav().className).toContain("md:w-(--panel-width-open)");
    expect(link("Apple").querySelector("span:last-child")?.className).not.toContain("md:hidden");
    await act(async () => button("Close menu").click());
    expect(window.localStorage.getItem(SIDE_PANEL_KEY)).toBe("false");
  });

  it("starts open when stored open", async () => {
    window.localStorage.setItem(SIDE_PANEL_KEY, "true");
    await render();
    expect(nav().className).toContain("md:w-(--panel-width-open)");
  });

  it("is off screen on phones until the drawer opens", async () => {
    await render();
    expect(nav().className.split(" ")).toContain("hidden");
    await render(true);
    expect(nav().className).toContain("fixed");
  });

  it("closes the drawer on Escape, on the backdrop and on choosing an entry, without saving it", async () => {
    await render(true);
    await act(async () => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(onDrawerClose).toHaveBeenCalledTimes(1);
    await act(async () => {
      (host.querySelector('[data-side-panel="backdrop"]') as HTMLElement).click();
    });
    expect(onDrawerClose).toHaveBeenCalledTimes(2);
    await act(async () => link("Apple").click());
    expect(onDrawerClose).toHaveBeenCalledTimes(3);
    expect(window.localStorage.getItem(SIDE_PANEL_KEY)).toBeNull();
  });

  it("shows the alias and count", async () => {
    await render();
    expect(host.querySelector('[data-side-panel="identity"]')?.textContent).toBe("ana5 recipes2 notebooks");
  });

  it("shows a zero count, and the singular and Spanish forms", async () => {
    fetchSidePanel.mockResolvedValue({ default_kitchen_id: "k1", recipes_added: 0, notebooks: 2 });
    await render();
    expect(host.textContent).toContain("0 recipes");
    fetchSidePanel.mockResolvedValue({ default_kitchen_id: "k1", recipes_added: 1, notebooks: 2 });
    await act(async () => requestSidePanelRefresh());
    expect(host.textContent).toContain("1 recipe");
    locale = "es";
    fetchSidePanel.mockResolvedValue({ default_kitchen_id: "k1", recipes_added: 2, notebooks: 2 });
    await render();
    await act(async () => requestSidePanelRefresh());
    expect(host.textContent).toContain("2 recetas");
  });

  it("shows no number when the count fails, and keeps working", async () => {
    fetchSidePanel.mockResolvedValue(null);
    await render();
    expect(host.querySelector('[data-side-panel="identity"]')?.textContent).toBe("ana");
    expect(link("Notebooks")).toBeTruthy();
  });

  it("shows a short error when the kitchens fail, and keeps the other entries", async () => {
    fetchKitchens.mockResolvedValue({ ok: false, error: "Could not load" });
    await render();
    expect(host.querySelector('[role="alert"]')?.textContent).toBe("Could not load");
    expect(button("Log out")).toBeTruthy();
  });

  it("ends with log out, which disables itself while it runs", async () => {
    await render();
    expect(names().at(-1)).toBe("Log out");
    await act(async () => button("Log out").click());
    expect(signOut).toHaveBeenCalledWith("/sign-in");
    expect(button("Logging out…").disabled).toBe(true);
  });

  it("swaps kitchen entries for archived ones with the toggle", async () => {
    await render();
    await act(async () => button("Show archived kitchens").click());
    expect(link("Old")).toBeTruthy();
    expect(link("Apple")).toBeNull();
    expect(link("Notebooks")).toBeTruthy();
  });

  it("says when nothing is archived", async () => {
    stubKitchens(KITCHENS, []);
    await render();
    await act(async () => button("Show archived kitchens").click());
    expect(host.textContent).toContain("No archived kitchens.");
  });

  it("adds a kitchen from an inline row, with no dialog", async () => {
    createKitchen.mockResolvedValue({ ok: true, kitchen: {} });
    await render();
    await act(async () => button("Create kitchen").click());
    expect(document.querySelector('[role="dialog"]')).toBeNull();
    expect(window.localStorage.getItem(SIDE_PANEL_KEY)).toBe("true");
    const input = host.querySelector("li input") as HTMLInputElement;
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, "Beach");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => button("Save").click());
    expect(createKitchen.mock.calls[0][0]).toBe("Beach");
    expect(host.querySelector("li input")).toBeNull();
    expect(refresh).toHaveBeenCalled();
  });

  it("hides the row on a click outside, but not on one inside or on the plus", async () => {
    const press = (el: Element) => el.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true }));
    await render();
    await act(async () => button("Create kitchen").click());
    await act(async () => {
      press(host.querySelector("li input") as Element);
      press(button("Create kitchen"));
    });
    expect(host.querySelector("li input")).toBeTruthy();
    await act(async () => press(document.body));
    expect(host.querySelector("li input")).toBeNull();
  });

  it("refuses a blank name and cancels on Escape", async () => {
    await render();
    await act(async () => button("Create kitchen").click());
    await act(async () => button("Save").click());
    expect(host.querySelector('[role="alert"]')?.textContent).toBe("Enter a kitchen name.");
    expect(createKitchen).not.toHaveBeenCalled();
    await act(async () => {
      host
        .querySelector("li input")
        ?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });
    expect(host.querySelector("li input")).toBeNull();
    expect(onDrawerClose).not.toHaveBeenCalled();
  });
});
