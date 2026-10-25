/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { kitchensMessages } from "@/lib/i18n/kitchens";
import type { KitchenItem } from "./kitchensClient";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/home",
}));

vi.mock("@/components/PreferencesProvider", () => ({
  usePreferences: () => ({ locale: "en" }),
}));

vi.mock("./kitchens.module.scss", () => ({
  default: new Proxy(
    {},
    {
      get: (_t, prop) => String(prop),
    },
  ),
}));

import { KitchensPanel } from "./KitchensPanel";
import { resetMembershipKitchensStore } from "./membershipKitchensStore";

const t = kitchensMessages.en;

const solo: KitchenItem = {
  id: "personal",
  name: "Personal",
  owner_id: "owner-1",
  role: "owner",
  members: [{ user_id: "owner-1", alias: "sebas" }],
};

const shared: KitchenItem = {
  id: "home",
  name: "Home",
  owner_id: "owner-1",
  role: "owner",
  members: [
    { user_id: "owner-1", alias: "sebas" },
    { user_id: "member-2", alias: "alex" },
    { user_id: "member-3", alias: null },
  ],
};

function chipTexts(card: Element | null): string[] {
  return Array.from(card?.querySelectorAll(".chipRow span") ?? []).map(
    (el) => el.textContent ?? "",
  );
}

describe("KitchensPanel roster chips", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    resetMembershipKitchensStore();
  });

  it("shows the owner bookmark and no balance column on a solo kitchen", () => {
    act(() => {
      root.render(
        <KitchensPanel
          initialKitchens={[solo]}
          currentUserId="owner-1"
        />,
      );
    });
    const card = container.querySelector('[aria-label="Open kitchen: Personal"]');
    expect(card?.querySelector(".roleBookmark")?.querySelector("svg")).not.toBeNull();
    expect(card?.querySelector('[aria-label="Owner"]')).not.toBeNull();
    expect(chipTexts(card)).toEqual([]);
    expect(card?.querySelector(".cardBalanceCol")).toBeNull();
    expect(card?.textContent).not.toContain("sebas");
  });

  it("sorts aliases A–Z and colors only the owner chip", () => {
    act(() => {
      root.render(<KitchensPanel initialKitchens={[shared]} currentUserId="owner-1" />);
    });
    const card = container.querySelector('[aria-label="Open kitchen: Home"]');
    expect(chipTexts(card)).toEqual(["alex", "member-3…"]);
    const chips = Array.from(card?.querySelectorAll(".chipRow span") ?? []);
    const otherChip = chips.find((el) => el.textContent === "alex");
    expect(chips.every((el) => !el.className.includes("accent"))).toBe(true);
    expect(otherChip?.className).not.toContain("accent");
  });

  it("uses a users-icon bookmark and still shows the owner when the viewer is a member", () => {
    act(() => {
      root.render(
        <KitchensPanel
          initialKitchens={[{ ...shared, role: "member" }]}
          currentUserId="member-2"
        />,
      );
    });
    const card = container.querySelector('[aria-label="Open kitchen: Home"]');
    expect(card?.querySelector(".roleBookmark")?.querySelector("svg")).not.toBeNull();
    expect(card?.querySelector('[aria-label="Member"]')).not.toBeNull();
    expect(chipTexts(card)).toEqual(["member-3…", "sebas"]);
    const chips = Array.from(card?.querySelectorAll(".chipRow span") ?? []);
    const ownerChip = chips.find((el) => el.textContent === "sebas");
    expect(ownerChip?.className).toContain("accent");
    expect(chipTexts(card)).not.toContain("alex");
  });
});

function openMenu(container: HTMLDivElement, kitchenName: string) {
  const card = container.querySelector(`[aria-label="Open kitchen: ${kitchenName}"]`);
  const menuButton = card?.parentElement?.querySelector(
    `[aria-label="${t.menuAria}"]`,
  ) as HTMLButtonElement | null;
  act(() => {
    menuButton?.click();
  });
}

describe("KitchensPanel archive toggle", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    resetMembershipKitchensStore();
    vi.unstubAllGlobals();
  });

  it("shows the create input and an Archive menu item for the owner when showArchived is false", () => {
    act(() => {
      root.render(<KitchensPanel initialKitchens={[solo]} currentUserId="owner-1" />);
    });
    expect(container.querySelector(`[placeholder="${t.createLabel}"]`)).not.toBeNull();
    openMenu(container, "Personal");
    const items = Array.from(container.querySelectorAll('[role="menuitem"]')).map(
      (el) => el.textContent,
    );
    expect(items).toContain(t.kitchensArchive);
    expect(items).not.toContain(t.kitchensUnarchive);
  });

  it("shows no kitchen menu to a non-owner member, since archive is owner-only", () => {
    act(() => {
      root.render(
        <KitchensPanel initialKitchens={[{ ...shared, role: "member" }]} currentUserId="member-2" />,
      );
    });
    const card = container.querySelector(`[aria-label="Open kitchen: Home"]`);
    expect(card?.parentElement?.querySelector(`[aria-label="${t.menuAria}"]`)).toBeNull();
  });

  it("hides the create input and fetches archived kitchens when showArchived is true", async () => {
    const archived: KitchenItem = { ...solo, id: "archived-1", name: "Old kitchen", is_archived: true };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ kitchens: [archived] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await act(async () => {
      root.render(
        <KitchensPanel initialKitchens={[solo]} currentUserId="owner-1" showArchived />,
      );
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/kitchens?archived=true",
      expect.objectContaining({ method: "GET" }),
    );
    expect(container.querySelector(`[placeholder="${t.createLabel}"]`)).toBeNull();
    expect(container.textContent).toContain("Old kitchen");
    expect(container.textContent).not.toContain("Personal");
  });

  it("shows Unarchive (not the full owner menu) for an owned kitchen in the archived view", async () => {
    const archived: KitchenItem = { ...solo, id: "archived-1", name: "Old kitchen", is_archived: true };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ kitchens: [archived] }),
      }),
    );

    await act(async () => {
      root.render(<KitchensPanel initialKitchens={[]} currentUserId="owner-1" showArchived />);
    });

    openMenu(container, "Old kitchen");
    const items = Array.from(container.querySelectorAll('[role="menuitem"]')).map(
      (el) => el.textContent,
    );
    expect(items).toEqual([t.kitchensUnarchive]);
  });
});
