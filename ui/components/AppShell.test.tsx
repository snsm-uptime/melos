/** @vitest-environment jsdom */

import { act, useEffect, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useChromeBack, useChromeHeader } from "@/components/ChromeBack";
import { useToast } from "@/components/Toast";
import { AppShell } from "./AppShell";

const push = vi.fn();
let pathname = "/upload";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ push }),
}));

vi.mock("@/components/PreferencesProvider", () => ({
  usePreferences: () => ({ locale: "en", theme: "light" }),
}));

// The quick add reads notebooks; QuickAddRecipe.test.tsx covers it (spec 069).
vi.mock("@/components/QuickAddRecipe", () => ({
  QuickAddRecipe: () => <button type="button" aria-label="Add recipe" data-quick-add />,
}));

vi.mock("@/components/IconButton/IconButton.module.scss", () => ({
  default: new Proxy(
    {},
    {
      get: (_t, prop) => String(prop),
    },
  ),
}));

function EnableBack({ href }: { href: string }) {
  useChromeBack(href);
  return <p>screen</p>;
}

function EnableHeader({
  href,
  title,
  details,
  onBack,
  progressBar,
}: {
  href?: string;
  title?: string;
  details?: string;
  onBack?: () => void;
  progressBar?: ReactNode;
}) {
  useChromeHeader({ backHref: href, title, details, onBack, progressBar });
  return <p>screen</p>;
}

describe("AppShell chrome header", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    push.mockReset();
    pathname = "/upload";
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

  it("hides the back control when no screen has opted in", async () => {
    await act(async () => {
      root.render(
        <AppShell>
          <p>home</p>
        </AppShell>,
      );
    });

    expect(container.querySelector('button[aria-label="Back"]')).toBeNull();
  });

  it("shows a chevron back control that pushes the opted-in href", async () => {
    await act(async () => {
      root.render(
        <AppShell>
          <EnableBack href="/upload" />
        </AppShell>,
      );
    });

    const back = container.querySelector('button[aria-label="Back"]') as HTMLButtonElement;
    expect(back).toBeTruthy();
    expect(back.querySelector("svg")).toBeTruthy();

    await act(async () => {
      back.click();
    });
    expect(push).toHaveBeenCalledWith("/upload");
    expect(push).toHaveBeenCalledTimes(1);
  });

  it("hides the header on auth routes when no screen opts in", async () => {
    pathname = "/sign-in";
    await act(async () => {
      root.render(
        <AppShell>
          <p>screen</p>
        </AppShell>,
      );
    });

    expect(container.querySelector("header")).toBeNull();
    expect(container.querySelector('button[aria-label="Back"]')).toBeNull();
  });

  it("shows the header (with back) on auth routes like /sign-in when a screen opts in, but never the TabBar there", async () => {
    pathname = "/sign-in";
    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader href="/" title="Melos" />
        </AppShell>,
      );
    });

    const header = container.querySelector("header");
    expect(header).toBeTruthy();
    expect(header?.querySelector("h1")?.textContent).toBe("Melos");
    const back = header?.querySelector('button[aria-label="Back"]') as HTMLButtonElement;
    expect(back).toBeTruthy();

    await act(async () => {
      back.click();
    });
    expect(push).toHaveBeenCalledWith("/");

    // Auth routes never gain the authenticated TabBar, opted-in header or not.
    expect(container.querySelector("nav")).toBeNull();
  });

  it("shows the panel on authenticated routes, with the quick add in the panel", async () => {
    pathname = "/home";
    await act(async () => {
      root.render(
        <AppShell>
          <p>screen</p>
        </AppShell>,
      );
    });

    expect(container.querySelector("header")?.className).toContain("md:hidden");
    expect(container.querySelector("nav [data-quick-add]")).toBeTruthy();
    expect(container.querySelector("header [data-quick-add]")).toBeNull();
    expect(container.querySelector("nav")).toBeTruthy();
  });

  it("shows the panel where only the screen asks for it, and not without it (spec 055)", async () => {
    pathname = "/admin";
    function Dashboard() {
      useChromeHeader({ title: "Dashboard", sidePanel: true });
      return <p>dashboard</p>;
    }
    await act(async () => {
      root.render(
        <AppShell>
          <Dashboard />
        </AppShell>,
      );
    });
    expect(container.querySelector("nav")).not.toBeNull();

    await act(async () => {
      root.render(
        <AppShell>
          <p>not found</p>
        </AppShell>,
      );
    });
    expect(container.querySelector("nav")).toBeNull();
  });

  it("keeps the same panel from another page into the dashboard, and drops it for its not-found page", async () => {
    pathname = "/notebooks";
    function Dashboard() {
      useChromeHeader({ title: "Dashboard", sidePanel: true });
      return <p>dashboard</p>;
    }
    await act(async () => {
      root.render(
        <AppShell>
          <p>notebooks</p>
        </AppShell>,
      );
    });
    const panel = container.querySelector("nav");
    expect(panel).not.toBeNull();

    // A remounted panel would be a new element, loading its kitchens and counts again.
    pathname = "/admin";
    await act(async () => {
      root.render(
        <AppShell>
          <Dashboard />
        </AppShell>,
      );
    });
    expect(container.querySelector("nav")).toBe(panel);

    pathname = "/notebooks";
    await act(async () => {
      root.render(
        <AppShell>
          <p>notebooks</p>
        </AppShell>,
      );
    });
    pathname = "/admin";
    await act(async () => {
      root.render(
        <AppShell>
          <p>not found</p>
        </AppShell>,
      );
    });
    expect(container.querySelector("nav")).toBeNull();
  });

  it("opens the drawer from the header's menu button", async () => {
    pathname = "/notebooks";
    await act(async () => {
      root.render(
        <AppShell>
          <p>screen</p>
        </AppShell>,
      );
    });
    const panel = () => container.querySelector('[data-side-panel="panel"]') as HTMLElement;
    const backdrop = () => container.querySelector('[data-side-panel="backdrop"]') as HTMLElement;
    expect(panel().className).toContain("max-md:-translate-x-full");
    await act(async () => {
      (container.querySelector('header button[aria-label="Open menu"]') as HTMLElement).click();
    });
    expect(panel().className).not.toContain("max-md:-translate-x-full");
    expect(backdrop().className).not.toContain("invisible");
  });

  it("renders title and details on the same header row as back", async () => {
    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader href="/upload" title="Review statements" details="12 left" />
        </AppShell>,
      );
    });

    const header = container.querySelector("header");
    expect(header).toBeTruthy();
    expect(header?.getAttribute("data-app-chrome")).toBe("header");
    const heading = header!.querySelector("h1");
    expect(heading?.textContent).toBe("Review statements");
    expect(header!.textContent).toContain("12 left");
    expect(header!.querySelector('button[aria-label="Back"]')).toBeTruthy();
  });

  it("runs onBack instead of pushing backHref when both are set", async () => {
    const onBack = vi.fn();
    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader href="/upload" title="Review statements" onBack={onBack} />
        </AppShell>,
      );
    });

    const back = container.querySelector('button[aria-label="Back"]') as HTMLButtonElement;
    await act(async () => {
      back.click();
    });
    expect(onBack).toHaveBeenCalledTimes(1);
    expect(push).not.toHaveBeenCalled();
  });

  it("keeps the opted-in progressBar in the sticky frosted bar with the header", async () => {
    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader
            href="/budgets/b1"
            title="Groceries"
            progressBar={<div data-testid="progress-strip">bar</div>}
          />
        </AppShell>,
      );
    });

    const strip = container.querySelector('[data-testid="progress-strip"]');
    const header = container.querySelector('header[data-app-chrome="header"]');
    expect(strip).toBeTruthy();
    // Same sticky wrapper as the header, so the strip stays at the very top while content scrolls.
    expect(header?.parentElement?.contains(strip)).toBe(true);
    expect(header?.parentElement?.classList.contains("frost-bar")).toBe(true);
  });

  it("puts the header in the main scroller as a sticky frosted bar", async () => {
    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader href="/budgets/b1" title="Groceries" />
        </AppShell>,
      );
    });

    const header = container.querySelector('header[data-app-chrome="header"]') as HTMLElement;
    const bar = header.parentElement as HTMLElement;
    const scroller = container.querySelector(".overflow-y-auto") as HTMLElement;
    expect(scroller.contains(header)).toBe(true);
    expect(bar.classList.contains("frost-bar")).toBe(true);
    expect(bar.classList.contains("sticky")).toBe(true);
    expect(bar.classList.contains("top-0")).toBe(true);
    expect(bar.getAttribute("data-frosted")).toBe("false");
  });

  it("frosts the header once the main scroller has been scrolled, and clears it at the top", async () => {
    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader href="/budgets/b1" title="Groceries" />
        </AppShell>,
      );
    });

    const scroller = container.querySelector(".overflow-y-auto") as HTMLElement;
    const bar = container.querySelector('header[data-app-chrome="header"]')?.parentElement as HTMLElement;

    await act(async () => {
      scroller.scrollTop = 1;
      scroller.dispatchEvent(new Event("scroll"));
    });
    expect(bar.getAttribute("data-frosted")).toBe("true");

    await act(async () => {
      scroller.scrollTop = 0;
      scroller.dispatchEvent(new Event("scroll"));
    });
    expect(bar.getAttribute("data-frosted")).toBe("false");
  });

  it("omits the progressBar strip when not opted in", async () => {
    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader href="/budgets/b1" title="Groceries" />
        </AppShell>,
      );
    });

    expect(container.querySelector('[data-testid="progress-strip"]')).toBeNull();
  });

  it("shows the header when a screen opts in with title only", async () => {
    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader title="Account" />
        </AppShell>,
      );
    });

    expect(container.querySelector("header h1")?.textContent).toBe("Account");
    expect(container.querySelector('button[aria-label="Back"]')).toBeNull();
  });

  it("puts the panel entry's icon before the title of a page the panel opens, not one with Back", async () => {
    const icon = () => container.querySelector('[data-app-chrome="title-icon"]');
    pathname = "/kitchens/k1";
    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader title="Home" />
        </AppShell>,
      );
    });
    expect(icon()?.nextElementSibling?.tagName).toBe("H1");

    pathname = "/upload";
    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader title="Upload" />
        </AppShell>,
      );
    });
    expect(icon()).toBeNull();

    pathname = "/recipes/r1";
    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader title="Soup" href="/notebooks" />
        </AppShell>,
      );
    });
    expect(icon()).toBeNull();
  });

  it("insets a leading avatar by the page gutter, and a Back button by the tighter chrome inset", async () => {
    function AvatarHeader() {
      useChromeHeader({ leading: <span>avatar</span>, title: "Kitchens" });
      return null;
    }
    await act(async () => {
      root.render(
        <AppShell>
          <AvatarHeader />
        </AppShell>,
      );
    });
    const header = container.querySelector("header") as HTMLElement;
    expect(header.className).toContain("pl-[max(var(--page-gutter)");

    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader href="/home" title="Kitchen" />
        </AppShell>,
      );
    });
    expect((container.querySelector("header") as HTMLElement).className).toContain("pl-[max(0.5rem");
  });

  it("insets a kitchen title by the page gutter on larger screens, past the phone menu button", async () => {
    pathname = "/kitchens/k1";
    await act(async () => {
      root.render(
        <AppShell>
          <EnableHeader title="Kitchen" />
        </AppShell>,
      );
    });
    const { className } = container.querySelector("header") as HTMLElement;
    expect(className).toContain("md:pl-[max(var(--page-gutter)");
    expect(className).toContain(" pl-[max(0.5rem");
    expect(className).toContain("pr-[max(var(--page-gutter)");
  });

  describe("signed-out language switch (spec 063)", () => {
    const switchPresent = () => container.querySelector('[role="group"]') !== null;

    function renderAt(path: string, child: ReactNode) {
      pathname = path;
      act(() => {
        root.render(<AppShell>{child}</AppShell>);
      });
    }

    it("does not float on /sign-in, which has the switch in its own card", () => {
      renderAt("/sign-in", <EnableHeader href="/" title="Melos" />);
      expect(container.querySelector('[data-app-chrome="header"]')).not.toBeNull();
      expect(switchPresent()).toBe(false);
    });

    it("shows on a signed-out screen that has no header", () => {
      renderAt("/invites/accept", <p>screen</p>);
      expect(container.querySelector('[data-app-chrome="header"]')).toBeNull();
      expect(switchPresent()).toBe(true);
    });

    it.each(["/home", "/alias"])("does not show on %s", (path) => {
      renderAt(path, <p>screen</p>);
      expect(switchPresent()).toBe(false);
    });
  });

  it("puts the toast viewport at the bottom of the content area, beside the panel (spec 064)", async () => {
    pathname = "/home";
    const grabbed: { show: (toast: { id: string; text: string }) => void } = { show: () => {} };
    function Shout({ onShow }: { onShow: (show: typeof grabbed.show) => void }) {
      const { show } = useToast();
      useEffect(() => {
        onShow(show);
      }, [show, onShow]);
      return null;
    }
    const onShow = (show: typeof grabbed.show) => (grabbed.show = show);
    await act(async () => {
      root.render(
        <AppShell>
          <Shout onShow={onShow} />
        </AppShell>,
      );
    });
    await act(async () => grabbed.show({ id: "t", text: "ben is editing the cart" }));
    const viewport = container.querySelector("[data-toast-viewport]") as HTMLElement;
    const nav = container.querySelector("nav") as HTMLElement;
    expect(viewport.textContent).toBe("ben is editing the cart");
    expect(viewport.className).toContain("absolute");
    expect(viewport.parentElement?.contains(nav)).toBe(false);
    expect(viewport.className).toContain("safe-area-inset-bottom");
  });
});
