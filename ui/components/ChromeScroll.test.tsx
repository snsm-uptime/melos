/** @vitest-environment jsdom */

import { act, useRef, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

let pathname = "/notebooks";
vi.mock("next/navigation", () => ({ usePathname: () => pathname }));

import { ChromeScrollProvider, useChromeScrolled } from "./ChromeScroll";

const renderSpy = vi.fn();
function Probe() {
  renderSpy();
  return <output>{String(useChromeScrolled())}</output>;
}

function Harness({ children }: { children: ReactNode }) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  return (
    <div ref={scrollerRef} data-scroller>
      <ChromeScrollProvider scrollerRef={scrollerRef}>{children}</ChromeScrollProvider>
    </div>
  );
}

describe("ChromeScroll", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    pathname = "/notebooks";
    renderSpy.mockClear();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  function scroller(): HTMLDivElement {
    return container.querySelector("[data-scroller]") as HTMLDivElement;
  }

  function scrollTo(top: number) {
    act(() => {
      scroller().scrollTop = top;
      scroller().dispatchEvent(new Event("scroll"));
    });
  }

  it("is false at mount, true once scrolled, and false again back at the top", () => {
    act(() => root.render(<Harness><Probe /></Harness>));
    expect(container.querySelector("output")?.textContent).toBe("false");

    scrollTo(1);
    expect(container.querySelector("output")?.textContent).toBe("true");

    scrollTo(0);
    expect(container.querySelector("output")?.textContent).toBe("false");
  });

  it("re-renders the consumer only when the value flips", () => {
    act(() => root.render(<Harness><Probe /></Harness>));
    const afterMount = renderSpy.mock.calls.length;

    scrollTo(5);
    scrollTo(10);
    expect(renderSpy.mock.calls.length).toBe(afterMount + 1);
  });

  it("re-reads the position on a route change", () => {
    act(() => root.render(<Harness><Probe /></Harness>));
    scrollTo(40);
    expect(container.querySelector("output")?.textContent).toBe("true");

    // The new page opens at the top: the position is read again on the route change.
    scroller().scrollTop = 0;
    pathname = "/kitchens";
    act(() => root.render(<Harness><Probe /></Harness>));
    expect(container.querySelector("output")?.textContent).toBe("false");
  });

  it("returns false outside a provider", () => {
    act(() => root.render(<Probe />));
    expect(container.querySelector("output")?.textContent).toBe("false");
  });
});
