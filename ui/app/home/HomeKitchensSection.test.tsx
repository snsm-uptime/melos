/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { kitchensMessages } from "@/lib/i18n/kitchens";
import type { KitchenItem } from "@/app/kitchens/kitchensClient";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/home",
}));

vi.mock("@/components/PreferencesProvider", () => ({
  usePreferences: () => ({ locale: "en" }),
}));

vi.mock("@/app/kitchens/kitchens.module.scss", () => ({
  default: new Proxy(
    {},
    {
      get: (_t, prop) => String(prop),
    },
  ),
}));

import { AppShell } from "@/components/AppShell";
import { HomeKitchensSection } from "./HomeKitchensSection";
import { resetMembershipKitchensStore } from "@/app/kitchens/membershipKitchensStore";

const t = kitchensMessages.en;

const solo: KitchenItem = {
  id: "personal",
  name: "Personal",
  owner_id: "owner-1",
  role: "owner",
  members: [{ user_id: "owner-1", alias: "sebas" }],
};

describe("HomeKitchensSection", () => {
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

  it("starts with the toggle OFF: create input visible, non-archived kitchens shown", () => {
    act(() => {
      root.render(
        <AppShell>
          <HomeKitchensSection
            title="Kitchens"
            alias="sebas"
            userId="owner-1"
            photoBase64={null}
            initialKitchens={[solo]}
            currentUserId="owner-1"
          />
        </AppShell>,
      );
    });

    expect(container.querySelector(`[placeholder="${t.createLabel}"]`)).not.toBeNull();
    expect(container.textContent).toContain("Personal");
    const header = container.querySelector('[data-app-chrome="header"]') as HTMLElement;
    const toggle = header.querySelector('[aria-pressed]') as HTMLButtonElement;
    expect(toggle.getAttribute("aria-pressed")).toBe("false");
  });

  it("clicking the chrome's box icon flips KitchensPanel into archived mode and fetches archived kitchens", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ kitchens: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    act(() => {
      root.render(
        <AppShell>
          <HomeKitchensSection
            title="Kitchens"
            alias="sebas"
            userId="owner-1"
            photoBase64={null}
            initialKitchens={[solo]}
            currentUserId="owner-1"
          />
        </AppShell>,
      );
    });

    const header = container.querySelector('[data-app-chrome="header"]') as HTMLElement;
    const toggle = header.querySelector('[aria-pressed]') as HTMLButtonElement;

    await act(async () => {
      toggle.click();
    });

    expect(toggle.getAttribute("aria-pressed")).toBe("true");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/kitchens?archived=true",
      expect.objectContaining({ method: "GET" }),
    );
    expect(container.querySelector(`[placeholder="${t.createLabel}"]`)).toBeNull();

    await act(async () => {
      toggle.click();
    });

    expect(toggle.getAttribute("aria-pressed")).toBe("false");
    expect(container.querySelector(`[placeholder="${t.createLabel}"]`)).not.toBeNull();
    expect(container.textContent).toContain("Personal");
  });
});
