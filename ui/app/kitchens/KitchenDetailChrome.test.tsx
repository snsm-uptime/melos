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
import { KitchenDetailChrome } from "./KitchenDetailChrome";

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
});
