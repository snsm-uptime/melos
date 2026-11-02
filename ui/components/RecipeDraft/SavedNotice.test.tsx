/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearCapture, getCaptureState, markSaved } from "@/lib/capture/captureStore";

import { SavedNotice } from "./SavedNotice";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

describe("SavedNotice", () => {
  let container: HTMLDivElement;
  let root: Root;

  const notice = () => container.querySelector('[role="status"]');

  beforeEach(() => {
    vi.useFakeTimers();
    clearCapture();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.useRealTimers();
  });

  it("shows for ten seconds, then goes away", () => {
    markSaved("/notebooks/nb-1");
    act(() => root.render(<SavedNotice returnPath="/notebooks/nb-1" />));
    expect(notice()).not.toBeNull();
    expect(getCaptureState().savedNotice).toBeNull();

    act(() => vi.advanceTimersByTime(9_999));
    expect(notice()).not.toBeNull();

    act(() => vi.advanceTimersByTime(1));
    expect(notice()).toBeNull();
  });

  it("shows nothing on a page the Save did not return to", () => {
    markSaved("/notebooks/nb-1");
    act(() => root.render(<SavedNotice returnPath="/notebooks/nb-2" />));
    expect(notice()).toBeNull();
  });
});
