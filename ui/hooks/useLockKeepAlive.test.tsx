/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useLockKeepAlive } from "./useLockKeepAlive";

const START = new Date("2026-10-29T12:00:00Z").getTime();
const EXPIRES = new Date(START + 5 * 60_000).toISOString();

type Hook = ReturnType<typeof useLockKeepAlive>;

describe("useLockKeepAlive", () => {
  let container: HTMLDivElement;
  let root: Root;
  let current: Hook;

  function Probe(props: Parameters<typeof useLockKeepAlive>[0]) {
    current = useLockKeepAlive(props);
    return null;
  }

  function render(keepAlive: () => void, idleExpiresAt: string | null = EXPIRES) {
    act(() => root.render(<Probe keepAlive={keepAlive} idleExpiresAt={idleExpiresAt} />));
  }

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(START);
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.useRealTimers();
  });

  it("sends nothing without activity, even when time passes", () => {
    const keepAlive = vi.fn();
    render(keepAlive);
    act(() => vi.advanceTimersByTime(3 * 60_000));
    expect(keepAlive).not.toHaveBeenCalled();
  });

  it("sends at most one keep-alive every 30 seconds while the member types", () => {
    const keepAlive = vi.fn();
    render(keepAlive);
    act(() => current.notifyActivity());
    act(() => vi.advanceTimersByTime(10_000));
    act(() => current.notifyActivity());
    expect(keepAlive).toHaveBeenCalledTimes(1);
    act(() => vi.advanceTimersByTime(20_000));
    act(() => current.notifyActivity());
    expect(keepAlive).toHaveBeenCalledTimes(2);
  });

  it("warns at 4 minutes and expires at 5", () => {
    render(vi.fn());
    expect(current.warning).toBe(false);
    act(() => vi.advanceTimersByTime(4 * 60_000));
    expect(current.warning).toBe(true);
    expect(current.expired).toBe(false);
    act(() => vi.advanceTimersByTime(60_000));
    expect(current.warning).toBe(false);
    expect(current.expired).toBe(true);
  });

  it("keepNow sends at once, and no lock means no warning", () => {
    const keepAlive = vi.fn();
    render(keepAlive, null);
    act(() => current.keepNow());
    expect(keepAlive).toHaveBeenCalledTimes(1);
    expect(current.warning).toBe(false);
    expect(current.expired).toBe(false);
  });
});
