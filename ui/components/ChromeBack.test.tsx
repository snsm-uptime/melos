/** @vitest-environment jsdom */

import { act, Fragment, StrictMode, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

let pathname = "/start";
vi.mock("next/navigation", () => ({ usePathname: () => pathname }));

import {
  ChromeBackProvider,
  useChromeHeader,
  useChromeHeaderState,
  type ChromeHeaderConfig,
} from "./ChromeBack";

function Screen({ header, children }: { header: ChromeHeaderConfig; children?: ReactNode }) {
  useChromeHeader(header);
  return <>{children}</>;
}

/** What AppShell would show: the title and Back target of the header on top. */
function Probe() {
  const header = useChromeHeaderState();
  return (
    <output>
      {header.title ?? "(no title)"}|{header.backHref ?? "(no back)"}
    </output>
  );
}

describe("ChromeBack header stack", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    pathname = "/start";
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  async function render(ui: ReactNode) {
    await act(async () => {
      root.render(
        <ChromeBackProvider>
          {ui}
          <Probe />
        </ChromeBackProvider>,
      );
    });
  }

  const shown = () => container.querySelector("output")?.textContent;

  it("shows nothing until a screen asks for a header", async () => {
    await render(null);
    expect(shown()).toBe("(no title)|(no back)");
  });

  it("shows the screen's title and Back target, and nothing once it has left for another route", async () => {
    await render(<Screen header={{ title: "Kitchen", backHref: "/home" }} />);
    expect(shown()).toBe("Kitchen|/home");

    pathname = "/elsewhere";
    await render(null);
    expect(shown()).toBe("(no title)|(no back)");
  });

  it("shows the screen opened on top, and pops back to the one beneath it", async () => {
    const parent = { title: "Kitchen", backHref: "/home" };
    const child = { title: "Notebook", backHref: "/kitchens/k1" };

    await render(
      <Screen header={parent}>
        <Screen header={child} />
      </Screen>,
    );
    expect(shown()).toBe("Notebook|/kitchens/k1");

    await render(<Screen header={parent} />);
    expect(shown()).toBe("Kitchen|/home");
  });

  it("pops several levels in the order they were opened", async () => {
    const levels = ["A", "B", "C"].map((title, index) => ({
      title,
      backHref: `/level/${index}`,
    }));
    const seen: string[] = [];
    for (const depth of [3, 2, 1]) {
      await render(depthTree(levels, depth));
      seen.push(shown() as string);
    }
    expect(seen).toEqual(["C|/level/2", "B|/level/1", "A|/level/0"]);
  });

  it("keeps the new screen's header when the old screen is removed after it was added", async () => {
    // The next screen sets up while the previous one is still mounted; the previous one's
    // cleanup then runs. It must not blank the header the new screen just set.
    await render(<Screen header={{ title: "Kitchen", backHref: "/home" }} />);
    await render(
      <>
        <Screen header={{ title: "Kitchen", backHref: "/home" }} />
        <Screen header={{ title: "Notebook", backHref: "/kitchens/k1" }} />
      </>,
    );
    expect(shown()).toBe("Notebook|/kitchens/k1");

    await render(<Screen header={{ title: "Notebook", backHref: "/kitchens/k1" }} />);
    expect(shown()).toBe("Notebook|/kitchens/k1");
  });

  it("lets a screen change its own title without moving above the screen on top of it", async () => {
    const top = { title: "Notebook", backHref: "/kitchens/k1" };
    await render(
      <>
        <Screen header={{ title: undefined, backHref: "/home" }} />
        <Screen header={top} />
      </>,
    );
    expect(shown()).toBe("Notebook|/kitchens/k1");

    // The lower screen finishes loading and sets its title.
    await render(
      <>
        <Screen header={{ title: "Kitchen", backHref: "/home" }} />
        <Screen header={top} />
      </>,
    );
    expect(shown()).toBe("Notebook|/kitchens/k1");

    await render(<Screen header={{ title: "Kitchen", backHref: "/home" }} />);
    expect(shown()).toBe("Kitchen|/home");
  });

  it("follows a title that loads after the screen mounted", async () => {
    await render(<Screen header={{ title: undefined, backHref: "/home" }} />);
    expect(shown()).toBe("(no title)|/home");

    await render(<Screen header={{ title: "Casa", backHref: "/home" }} />);
    expect(shown()).toBe("Casa|/home");
  });

  describe("remembered titles", () => {
    /** Moves to another route and shows these screens there, as a navigation would. */
    async function go(to: string, ui: ReactNode) {
      pathname = to;
      // Each route's screens are new instances, as in the app.
      await render(<Fragment key={to}>{ui}</Fragment>);
    }

    it("shows a route's title again while its screen has not set one yet", async () => {
      await go("/kitchens/k1", <Screen header={{ title: "Casa", backHref: "/home" }} />);
      await go("/notebooks/n1", <Screen header={{ title: "Cuaderno", backHref: "/kitchens/k1" }} />);
      expect(shown()).toBe("Cuaderno|/kitchens/k1");

      // Back to the kitchen: only the layout's Back is there while the page streams in.
      await go("/kitchens/k1", <Screen header={{ backHref: "/home" }} />);
      expect(shown()).toBe("Casa|/home");

      // The page arrives and sets its own title, which replaces the remembered one.
      await go(
        "/kitchens/k1",
        <Screen header={{ backHref: "/home" }}>
          <Screen header={{ title: "Casa nueva", backHref: "/home" }} />
        </Screen>,
      );
      expect(shown()).toBe("Casa nueva|/home");
    });

    it("shows the remembered title and Back even before any screen on the route has set a header", async () => {
      await go("/kitchens/k1", <Screen header={{ title: "Casa", backHref: "/home" }} />);
      await go("/notebooks/n1", <Screen header={{ title: "Cuaderno", backHref: "/kitchens/k1" }} />);

      await go("/kitchens/k1", null);

      expect(shown()).toBe("Casa|/home");
    });

    it("pops back through several routes in the order they were opened", async () => {
      await go("/a", <Screen header={{ title: "A", backHref: "/start" }} />);
      await go("/a/b", <Screen header={{ title: "B", backHref: "/a" }} />);
      await go("/a/b/c", <Screen header={{ title: "C", backHref: "/a/b" }} />);

      const seen: string[] = [shown() as string];
      for (const back of ["/a/b", "/a"]) {
        await go(back, null);
        seen.push(shown() as string);
      }

      expect(seen).toEqual(["C|/a/b", "B|/a", "A|/start"]);
    });

    it("shows nothing for a route it has never shown", async () => {
      await go("/kitchens/k1", <Screen header={{ title: "Casa", backHref: "/home" }} />);
      await go("/elsewhere", null);
      expect(shown()).toBe("(no title)|(no back)");
    });

    it("keeps a screen's own Back target, and only fills in the missing title", async () => {
      await go("/kitchens/k1", <Screen header={{ title: "Casa", backHref: "/home" }} />);
      await go("/kitchens/k1", <Screen header={{ backHref: "/other" }} />);
      expect(shown()).toBe("Casa|/other");
    });

    it("remembers a title that loaded after the screen mounted, and the newest one", async () => {
      await go("/notebooks/n1", <Screen header={{ title: undefined, backHref: "/home" }} />);
      await go("/notebooks/n1", <Screen header={{ title: "Cuaderno", backHref: "/home" }} />);
      await go("/notebooks/n1", <Screen header={{ title: "Cuaderno renombrado", backHref: "/home" }} />);
      await go("/start", null);

      await go("/notebooks/n1", <Screen header={{ backHref: "/home" }} />);

      expect(shown()).toBe("Cuaderno renombrado|/home");
    });

    it("does not store a title under the route the address moved to while the screen was unmounting", async () => {
      pathname = "/notebooks/n1";
      await render(<Screen header={{ title: "Cuaderno", backHref: "/home" }} />);
      // The address moves on first; the very same screen instance updates its title afterwards.
      pathname = "/kitchens/k1";
      await render(<Screen header={{ title: "Cuaderno 2", backHref: "/home" }} />);

      await go("/start", null);
      await go("/kitchens/k1", null);
      expect(shown()).toBe("(no title)|(no back)");

      // It stayed remembered under the route it belongs to, with the newest title.
      await go("/notebooks/n1", null);
      expect(shown()).toBe("Cuaderno 2|/home");
    });

    it("forgets the longest unused routes beyond a limit", async () => {
      for (let i = 0; i < 60; i++) {
        await go(`/r/${i}`, <Screen header={{ title: `T${i}`, backHref: "/home" }} />);
      }
      await go("/r/0", null);
      expect(shown()).toBe("(no title)|(no back)");
      await go("/r/59", null);
      expect(shown()).toBe("T59|/home");
    });
  });
});

function depthTree(levels: ChromeHeaderConfig[], depth: number): ReactNode {
  const build = (index: number): ReactNode =>
    index === depth ? null : <Screen header={levels[index]}>{build(index + 1)}</Screen>;
  return build(0);
}
describe("ChromeBack under StrictMode", () => {
  it("keeps a nested screen on top when its effects run twice", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <StrictMode>
          <ChromeBackProvider>
            <Screen header={{ backHref: "/home" }}>
              <Screen header={{ title: "Cart", backHref: "/kitchen" }} />
            </Screen>
            <Probe />
          </ChromeBackProvider>
        </StrictMode>,
      );
    });
    expect(container.querySelector("output")?.textContent).toBe("Cart|/kitchen");
    act(() => root.unmount());
    container.remove();
  });
});
