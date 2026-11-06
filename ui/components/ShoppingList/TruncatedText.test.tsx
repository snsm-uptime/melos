/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SHOW_DELAY_MS } from "@/components/Tooltip";

import { TruncatedText } from "./TruncatedText";

/** jsdom has no layout: report a text this wide in a box this wide. */
function stubWidths(scrollWidth: number, clientWidth: number) {
  vi.spyOn(HTMLElement.prototype, "scrollWidth", "get").mockReturnValue(scrollWidth);
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(clientWidth);
}

describe("TruncatedText", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    vi.useFakeTimers();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  function hover() {
    const text = container.querySelector("span") as HTMLElement;
    act(() => {
      text.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
      vi.advanceTimersByTime(SHOW_DELAY_MS);
    });
  }

  const bubble = () => document.querySelector('[data-testid="tooltip-bubble"]');

  it("shows the whole text in a tooltip when it is cut", () => {
    stubWidths(300, 120);
    act(() => root.render(<TruncatedText text="Extra virgin olive oil" />));
    hover();
    expect(bubble()?.textContent).toBe("Extra virgin olive oil");
  });

  it("has no tooltip when the text fits", () => {
    stubWidths(80, 120);
    act(() => root.render(<TruncatedText text="Milk" />));
    hover();
    expect(bubble()).toBeNull();
  });
});
