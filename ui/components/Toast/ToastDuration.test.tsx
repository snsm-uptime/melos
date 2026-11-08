/** @vitest-environment jsdom */

import { act, useEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TOAST_MS, ToastProvider, useToast, useToastState } from "./ToastProvider";

let container: HTMLDivElement;
let root: Root;
let api: ReturnType<typeof useToast> | null = null;

/** Hands the toast api to the test from an effect, not from render. */
function Probe({ onReady }: { onReady: (value: ReturnType<typeof useToast>) => void }) {
  const state = useToastState();
  const toast = useToast();
  useEffect(() => {
    onReady(toast);
  }, [toast, onReady]);
  return <p data-count={state?.toasts.length ?? 0}>{state?.toasts.map((t) => t.id).join(",")}</p>;
}

beforeEach(() => {
  vi.useFakeTimers();
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() =>
    root.render(
      <ToastProvider>
        <Probe onReady={(value) => (api = value)} />
      </ToastProvider>,
    ),
  );
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.useRealTimers();
});

const shown = () => container.querySelector("p")?.textContent ?? "";

describe("toast duration", () => {
  it("a toast with durationMs 10 s is still there at 9.9 s and gone at 10.1 s", () => {
    act(() => api?.show({ id: "picture-disclaimer", text: "x", durationMs: 10_000 }));
    act(() => vi.advanceTimersByTime(9_900));
    expect(shown()).toBe("picture-disclaimer");
    act(() => vi.advanceTimersByTime(200));
    expect(shown()).toBe("");
  });

  it("a toast with no durationMs still ends at TOAST_MS", () => {
    act(() => api?.show({ id: "plain", text: "x" }));
    act(() => vi.advanceTimersByTime(TOAST_MS - 100));
    expect(shown()).toBe("plain");
    act(() => vi.advanceTimersByTime(200));
    expect(shown()).toBe("");
  });

  it("a tap dismisses it at once", () => {
    act(() => api?.show({ id: "picture-disclaimer", text: "x", durationMs: 10_000 }));
    act(() => api?.dismiss("picture-disclaimer"));
    expect(shown()).toBe("");
  });

  it("showing the same id again restarts the timer with the new duration", () => {
    act(() => api?.show({ id: "d", text: "x", durationMs: 10_000 }));
    act(() => vi.advanceTimersByTime(8_000));
    act(() => api?.show({ id: "d", text: "x", durationMs: 10_000 }));
    act(() => vi.advanceTimersByTime(8_000));
    expect(shown()).toBe("d");
    act(() => vi.advanceTimersByTime(2_500));
    expect(shown()).toBe("");
  });
});
