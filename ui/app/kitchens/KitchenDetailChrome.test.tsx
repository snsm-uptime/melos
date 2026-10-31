/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
const refresh = vi.fn();
const archiveKitchen = vi.fn();
const unarchiveKitchen = vi.fn();
const deleteKitchen = vi.fn();
const renameKitchen = vi.fn();
const setDefaultKitchen = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
  usePathname: () => "/kitchens/l1",
}));

vi.mock("@/components/PreferencesProvider", () => ({
  usePreferences: () => ({ locale: "en" }),
}));

vi.mock("./kitchensClient", async (original) => ({
  ...(await original<typeof import("./kitchensClient")>()),
  fetchKitchens: async () => ({ ok: true, kitchens: [] }),
  archiveKitchen: (...args: unknown[]) => archiveKitchen(...args),
  unarchiveKitchen: (...args: unknown[]) => unarchiveKitchen(...args),
  deleteKitchen: (...args: unknown[]) => deleteKitchen(...args),
  renameKitchen: (...args: unknown[]) => renameKitchen(...args),
}));

vi.mock("@/lib/sidePanelClient", async (original) => ({
  ...(await original<typeof import("@/lib/sidePanelClient")>()),
  fetchSidePanel: async () => null,
  setDefaultKitchen: (...args: unknown[]) => setDefaultKitchen(...args),
}));

import { AppShell } from "@/components/AppShell";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { KitchenCartCountProvider, usePublishKitchenCartCount } from "./cartCount";
import {
  KitchenDetailChrome,
  type KitchenManage,
  type KitchenShare,
} from "./KitchenDetailChrome";

const t = kitchensMessages.en;

type CartProp = { href: string; label: string; locale: "en" | "es" };
const CART: CartProp = { href: "/kitchens/k1/cart", label: "Cart", locale: "en" };

/** Stands in for the notebooks section, which publishes the cart count. */
function Publisher({ count }: { count: number | null }) {
  usePublishKitchenCartCount(count);
  return null;
}

const share: KitchenShare = {
  kitchenId: "l1",
  ownerId: "u1",
  members: [
    { user_id: "u1", alias: "ana", photo_base64: null },
    { user_id: "u2", alias: "ben", photo_base64: null },
  ],
  membersLoadError: false,
  inviteMessages: {
    inviteTitle: t.inviteTitle,
    inviteLabel: t.inviteLabel,
    inviteSubmit: t.inviteSubmit,
    inviteSending: t.inviteSending,
    inviteSent: t.inviteSent,
    errorGeneric: t.errorGeneric,
    errorInvalidName: t.errorInvalidName,
    errorInvalidEmail: t.errorInvalidEmail,
    errorForbidden: t.errorInviteForbidden,
    errorUnauthorized: t.errorUnauthorized,
    errorAlreadyMember: t.errorAlreadyMember,
    errorSmtp: t.errorSmtp,
  },
  labels: {
    open: t.mobileInviteAria,
    close: t.mobileSheetClose,
    membersTitle: t.detailMembersTitle,
    ownerBadge: t.ownerBadge,
    loadError: t.loadError,
  },
};

describe("KitchenDetailChrome", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    push.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it("renders the kitchen title with no Back control and no help icon", async () => {
    await act(async () => {
      root.render(
        <AppShell>
          <KitchenDetailChrome title="Household" />
        </AppShell>,
      );
    });

    const header = container.querySelector("header");
    expect(header?.querySelector("h1")?.textContent).toBe("Household");
    expect(header?.querySelector('button[aria-label="Back"]')).toBeNull();
    expect(header?.querySelector('button[aria-label^="Learn more"]')).toBeNull();
  });

  async function renderWith(shareProp?: KitchenShare, cart?: CartProp) {
    await act(async () => {
      root.render(
        <AppShell>
          <KitchenDetailChrome title="Household" share={shareProp} cart={cart} />
        </AppShell>,
      );
    });
  }

  it("has no share button without share (not the owner)", async () => {
    await renderWith();
    expect(container.querySelector(`header button[aria-label="${t.mobileInviteAria}"]`)).toBeNull();
    expect(document.querySelector("[role=dialog]")).toBeNull();
  });

  it("puts the share button at the end of the chrome and opens a dialog with the invite form and members", async () => {
    await renderWith(share);

    const buttons = Array.from(container.querySelectorAll("header button"));
    expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual(["Open menu", t.mobileInviteAria]);
    expect(document.querySelector("[role=dialog]")).toBeNull();

    await act(async () => {
      (buttons[1] as HTMLButtonElement).click();
    });

    const dialog = document.querySelector("[role=dialog]") as HTMLElement;
    expect(dialog.querySelector("h2")?.textContent).toBe(t.inviteTitle);
    expect(dialog.querySelector("input[type=email]")).not.toBeNull();
    expect(dialog.textContent).toContain("ana");
    expect(dialog.textContent).toContain("ben");
    expect(dialog.textContent).toContain(t.ownerBadge);
  });

  it("closes the dialog with its Close button", async () => {
    await renderWith(share);
    await act(async () => {
      (container.querySelector(`header button[aria-label="${t.mobileInviteAria}"]`) as HTMLButtonElement).click();
    });

    const close = Array.from(document.querySelectorAll("[role=dialog] button")).find(
      (b) => b.textContent === t.mobileSheetClose,
    ) as HTMLButtonElement;
    await act(async () => {
      close.click();
    });

    expect(document.querySelector("[role=dialog]")).toBeNull();
  });

  it("shows the load error instead of members when they could not be read", async () => {
    await renderWith({ ...share, members: [], membersLoadError: true });
    await act(async () => {
      (container.querySelector(`header button[aria-label="${t.mobileInviteAria}"]`) as HTMLButtonElement).click();
    });
    expect(document.querySelector("[role=dialog] [role=alert]")?.textContent).toBe(t.loadError);
  });

  it("puts the cart button before the share button and opens the cart (spec 022)", async () => {
    await renderWith(share, CART);
    const buttons = Array.from(container.querySelectorAll("header button"));
    expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual([
      "Open menu",
      "Cart",
      t.mobileInviteAria,
    ]);
    await act(async () => {
      (buttons[1] as HTMLButtonElement).click();
    });
    expect(push).toHaveBeenCalledWith("/kitchens/k1/cart");
  });

  it("shows the cart button to a member who is not the owner", async () => {
    await renderWith(undefined, CART);
    const labels = Array.from(container.querySelectorAll("header button")).map((b) =>
      b.getAttribute("aria-label"),
    );
    expect(labels).toEqual(["Open menu", "Cart"]);
  });

  async function renderWithCount(count: number | null, cart: CartProp = CART) {
    await act(async () => {
      root.render(
        <AppShell>
          <KitchenCartCountProvider>
            <KitchenDetailChrome title="Household" cart={cart} />
            <Publisher count={count} />
          </KitchenCartCountProvider>
        </AppShell>,
      );
    });
  }

  function cartButton() {
    return container.querySelector('header button[aria-label^="Ca"]') as HTMLButtonElement;
  }

  it("shows the number of recipes in a circular badge on the cart icon's bottom right corner", async () => {
    await renderWithCount(3);
    const badge = cartButton().querySelector('[role="img"]') as HTMLElement;
    expect(badge.textContent).toBe("3");
    expect(badge.getAttribute("aria-label")).toBe("3 recipes");
    expect(badge.className).toContain("rounded-full");
    expect(badge.className).toContain("absolute");
    expect(badge.className).toContain("-bottom-1");
    expect(badge.className).toContain("-right-1.5");
    // Anchored to the icon, not to the button.
    expect(badge.parentElement?.className).toContain("relative");
    expect(badge.parentElement?.querySelector("svg")).not.toBeNull();
  });

  it("puts the count in the button's accessible name", async () => {
    await renderWithCount(1);
    expect(cartButton().getAttribute("aria-label")).toBe("Cart, 1 recipe");
  });

  it("names the count in Spanish", async () => {
    await renderWithCount(2, { ...CART, label: "Carrito", locale: "es" });
    expect(cartButton().getAttribute("aria-label")).toBe("Carrito, 2 recetas");
    expect(cartButton().querySelector('[role="img"]')?.getAttribute("aria-label")).toBe("2 recetas");
  });

  it("shows no badge for an empty or unknown cart", async () => {
    await renderWithCount(0);
    expect(cartButton().querySelector('[role="img"]')).toBeNull();
    expect(cartButton().getAttribute("aria-label")).toBe("Cart");

    await renderWithCount(null);
    expect(cartButton().querySelector('[role="img"]')).toBeNull();
  });

  it("follows the count when it changes", async () => {
    await renderWithCount(1);
    await renderWithCount(4);
    expect(cartButton().querySelector('[role="img"]')?.textContent).toBe("4");
  });

  it("shows no badge without the provider", async () => {
    await renderWith(undefined, CART);
    expect(cartButton().querySelector('[role="img"]')).toBeNull();
  });

  describe("kitchen actions (spec 064)", () => {
    const manage: KitchenManage = {
      kitchenId: "k1",
      name: "Household",
      isOwner: true,
      isArchived: false,
      isDefault: false,
      locale: "en",
    };
    const inRow = () =>
      Array.from(document.querySelectorAll('[role="menu"] button')).map((b) => b.textContent);
    const button = (label: string) =>
      (container.querySelector(`header button[aria-label="${label}"]`) ??
        Array.from(document.querySelectorAll('[role="menu"] button')).find(
          (b) => b.textContent === label,
        )) as HTMLButtonElement;
    const dialogButton = (text: string) =>
      Array.from(document.querySelectorAll('[role="dialog"] button')).find(
        (b) => b.textContent === text,
      ) as HTMLButtonElement;

    async function renderManage(next: Partial<KitchenManage> = {}) {
      await act(async () => {
        root.render(
          <AppShell>
            <KitchenDetailChrome title="Household" manage={{ ...manage, ...next }} />
          </AppShell>,
        );
      });
      const dots = button(t.menuAria);
      if (dots) await act(async () => dots.click());
    }

    beforeEach(() => vi.clearAllMocks());

    it("gives an owner every action", async () => {
      await renderManage();
      expect(inRow()).toEqual([
        "Set as default",
        "Rename kitchen",
        "Archive kitchen",
        t.deleteAria,
      ]);
    });

    it("gives a non-owner only set as default", async () => {
      await renderManage({ isOwner: false });
      expect(inRow()).toEqual(["Set as default"]);
    });

    it("gives an archived kitchen's owner only restore", async () => {
      await renderManage({ isArchived: true });
      expect(inRow()).toEqual(["Restore kitchen"]);
    });

    it("gives a non-owner of an archived kitchen nothing", async () => {
      await renderManage({ isArchived: true, isOwner: false });
      expect(inRow()).toEqual([]);
    });

    it("hides set as default on the default kitchen", async () => {
      await renderManage({ isDefault: true });
      expect(inRow()).not.toContain("Set as default");
    });

    it("sets the default and refreshes the page", async () => {
      setDefaultKitchen.mockResolvedValue({ default_kitchen_id: "k1", recipes_added: 0, notebooks: 2 });
      await renderManage();
      await act(async () => button("Set as default").click());
      expect(setDefaultKitchen).toHaveBeenCalledWith("k1");
      expect(refresh).toHaveBeenCalled();
    });

    it("goes to Home after archive", async () => {
      archiveKitchen.mockResolvedValue({ ok: true, kitchen: {} });
      await renderManage();
      await act(async () => button("Archive kitchen").click());
      expect(push).toHaveBeenCalledWith("/home");
    });

    it("stays when archive fails", async () => {
      archiveKitchen.mockResolvedValue({ ok: false, error: "No" });
      await renderManage();
      await act(async () => button("Archive kitchen").click());
      expect(push).not.toHaveBeenCalled();
    });

    it("confirms before delete, then goes to Home", async () => {
      deleteKitchen.mockResolvedValue({ ok: true });
      await renderManage();
      await act(async () => button(t.deleteAria).click());
      expect(deleteKitchen).not.toHaveBeenCalled();
      expect(document.body.textContent).toContain(t.deleteConfirm);
      await act(async () => dialogButton(t.deleteAction).click());
      expect(deleteKitchen.mock.calls[0][0]).toBe("k1");
      expect(push).toHaveBeenCalledWith("/home");
    });

    it("restores and stays on the kitchen", async () => {
      unarchiveKitchen.mockResolvedValue({ ok: true, kitchen: {} });
      await renderManage({ isArchived: true });
      await act(async () => button("Restore kitchen").click());
      expect(push).not.toHaveBeenCalled();
      expect(refresh).toHaveBeenCalled();
    });

    it("renames from a dialog that starts with the current name", async () => {
      renameKitchen.mockResolvedValue({ ok: true, kitchen: {} });
      await renderManage();
      await act(async () => button("Rename kitchen").click());
      expect((document.querySelector('[role="dialog"] input') as HTMLInputElement).value).toBe(
        "Household",
      );
      await act(async () => dialogButton("Save").click());
      expect(renameKitchen.mock.calls[0].slice(0, 2)).toEqual(["k1", "Household"]);
    });

    it("puts the actions behind the dots menu", async () => {
      await renderManage();
      expect(button(t.menuAria)).toBeTruthy();
    });
  });
});
