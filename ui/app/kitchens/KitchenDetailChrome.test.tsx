/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/kitchens/l1",
}));

vi.mock("@/components/PreferencesProvider", () => ({
  usePreferences: () => ({ locale: "en" }),
}));

import { AppShell } from "@/components/AppShell";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { KitchenDetailChrome, type KitchenShare } from "./KitchenDetailChrome";

const t = kitchensMessages.en;

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

  it("renders the kitchen title with a Back control and no help icon", async () => {
    await act(async () => {
      root.render(
        <AppShell>
          <KitchenDetailChrome title="Household" />
        </AppShell>,
      );
    });

    const header = container.querySelector("header");
    expect(header?.querySelector("h1")?.textContent).toBe("Household");
    expect(header?.querySelector('button[aria-label="Back"]')).toBeTruthy();
    expect(header?.querySelector('button[aria-label^="Learn more"]')).toBeNull();

    await act(async () => {
      (header!.querySelector('button[aria-label="Back"]') as HTMLButtonElement).click();
    });
    expect(push).toHaveBeenCalledWith("/home");
  });

  async function renderWith(shareProp?: KitchenShare) {
    await act(async () => {
      root.render(
        <AppShell>
          <KitchenDetailChrome title="Household" share={shareProp} />
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
    expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual(["Back", t.mobileInviteAria]);
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
});
