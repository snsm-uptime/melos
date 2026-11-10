/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DemoFrame } from "./DemoFrame";

type ObserverCallback = (entries: Partial<IntersectionObserverEntry>[]) => void;

let observerCallback: ObserverCallback | null = null;
const disconnect = vi.fn();
let reducedMotion = false;

class FakeIntersectionObserver {
  constructor(callback: ObserverCallback) {
    observerCallback = callback;
  }
  observe() {}
  unobserve() {}
  disconnect() {
    disconnect();
  }
  takeRecords() {
    return [];
  }
}

function fakeMatchMedia(query: string): MediaQueryList {
  return {
    matches: query.includes("reduce") ? reducedMotion : false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  } as MediaQueryList;
}

describe("DemoFrame (spec 075 contracts/landing-page.md)", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    observerCallback = null;
    disconnect.mockReset();
    reducedMotion = false;
    vi.stubGlobal("IntersectionObserver", FakeIntersectionObserver);
    vi.stubGlobal("matchMedia", fakeMatchMedia);
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  async function render() {
    await act(async () => {
      root.render(
        <DemoFrame
          id="shop"
          title="Two recipes, one shopping list"
          description="The list shows flour — 1 cup + 3 tbsp."
          pauseLabel="Pause demo"
          playLabel="Play demo"
        >
          <span>scene</span>
        </DemoFrame>,
      );
    });
  }

  const frame = () => container.querySelector<HTMLElement>('[role="group"]')!;
  const button = () => container.querySelector<HTMLButtonElement>("button");

  async function intersect(ratio: number) {
    await act(async () => {
      observerCallback?.([{ isIntersecting: ratio > 0, intersectionRatio: ratio }]);
    });
  }

  it("is labelled by its title, hides the scene from screen readers and reads its description", async () => {
    await render();

    expect(frame().getAttribute("aria-label")).toBe("Two recipes, one shopping list");
    const scene = container.querySelector('[aria-hidden="true"]');
    expect(scene?.textContent).toBe("scene");
    expect(container.textContent).toContain("The list shows flour — 1 cup + 3 tbsp.");
  });

  it("plays only while at least 35% of it is in view", async () => {
    await render();
    expect(frame().dataset.playing).toBe("false");
    expect(frame().dataset.started).toBe("false");

    await intersect(0.2);
    expect(frame().dataset.playing).toBe("false");

    await intersect(0.5);
    expect(frame().dataset.playing).toBe("true");
    expect(frame().dataset.started).toBe("true");

    await intersect(0);
    expect(frame().dataset.playing).toBe("false");
    // Paused in place, not reset to the still final state.
    expect(frame().dataset.started).toBe("true");
  });

  it("pauses and resumes with its button while in view", async () => {
    await render();
    await intersect(0.5);

    expect(button()?.getAttribute("aria-pressed")).toBe("false");
    expect(button()?.getAttribute("aria-label")).toBe("Pause demo");

    await act(async () => button()!.click());
    expect(button()?.getAttribute("aria-pressed")).toBe("true");
    expect(button()?.getAttribute("aria-label")).toBe("Play demo");
    expect(frame().dataset.playing).toBe("false");

    await act(async () => button()!.click());
    expect(frame().dataset.playing).toBe("true");
  });

  it("has no pause button when the visitor asks for reduced motion", async () => {
    reducedMotion = true;
    await render();
    await intersect(0.5);

    expect(button()).toBeNull();
  });

  it("stops observing when it unmounts", async () => {
    await render();
    act(() => root.unmount());
    expect(disconnect).toHaveBeenCalled();
    root = createRoot(container);
  });
});
