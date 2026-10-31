/** @vitest-environment jsdom */

import { act, createElement, useEffect } from "react";
import { renderToString } from "react-dom/server";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it } from "vitest";

import { SIDE_PANEL_KEY, useSidePanelState } from "./useSidePanelState";

let state: ReturnType<typeof useSidePanelState>;

function Probe() {
  const current = useSidePanelState();
  useEffect(() => {
    state = current;
  });
  return createElement("span", null, String(current.isOpen));
}

function mount() {
  const host = document.createElement("div");
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  act(() => createRoot(host).render(createElement(Probe)));
}

describe("useSidePanelState", () => {
  beforeEach(() => window.localStorage.clear());

  it("is closed when nothing is stored", () => {
    mount();
    expect(state.isOpen).toBe(false);
  });

  it("reads a stored open state", () => {
    window.localStorage.setItem(SIDE_PANEL_KEY, "true");
    mount();
    expect(state.isOpen).toBe(true);
  });

  it("stores each change as text", () => {
    mount();
    act(() => state.setOpen(true));
    expect(window.localStorage.getItem(SIDE_PANEL_KEY)).toBe("true");
    expect(state.isOpen).toBe(true);
    act(() => state.setOpen(false));
    expect(window.localStorage.getItem(SIDE_PANEL_KEY)).toBe("false");
  });

  it("is closed on the server", () => {
    window.localStorage.setItem(SIDE_PANEL_KEY, "true");
    expect(renderToString(createElement(Probe))).toContain("false");
  });
});
