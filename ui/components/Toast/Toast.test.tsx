/** @vitest-environment jsdom */

import { act, useEffect, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TOAST_MS, ToastProvider, ToastViewport, useToast, useToastDock } from "./index";

type Api = ReturnType<typeof useToast>;
const grabbed: { api: Api | null } = { api: null };
function Grab({ onApi = (next: Api) => (grabbed.api = next) }: { onApi?: (api: Api) => void }) {
  const api = useToast();
  useEffect(() => {
    onApi(api);
  }, [api, onApi]);
  return null;
}
const api = {
  show: (...args: Parameters<ReturnType<typeof useToast>["show"]>) => grabbed.api!.show(...args),
};
function Dock({ node }: { node: ReactNode }) {
  useToastDock(node);
  return null;
}

describe("Toast", () => {
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
    vi.useRealTimers();
  });

  function render(extra: ReactNode = null) {
    act(() =>
      root.render(
        <ToastProvider>
          <Grab />
          {extra}
          <ToastViewport />
        </ToastProvider>,
      ),
    );
  }
  const statuses = () =>
    Array.from(container.querySelectorAll('[role="status"]')).map((el) => el.textContent);

  it("shows a toast and closes it after 4 seconds", () => {
    render();
    act(() => api.show({ id: "a", text: "ben is editing the cart" }));
    expect(statuses()).toEqual(["ben is editing the cart"]);
    act(() => vi.advanceTimersByTime(TOAST_MS - 1));
    expect(statuses()).toHaveLength(1);
    act(() => vi.advanceTimersByTime(1));
    expect(statuses()).toEqual([]);
  });

  it("keeps a persistent toast, and a toast with the same id replaces it", () => {
    render();
    const onClick = vi.fn();
    act(() =>
      api.show({ id: "idle", text: "warn", persistent: true, action: { label: "Keep editing", onClick } }),
    );
    act(() => vi.advanceTimersByTime(60_000));
    expect(statuses()).toEqual(["warnKeep editing"]);
    act(() => container.querySelector("button")?.click());
    expect(onClick).toHaveBeenCalled();
    act(() => api.show({ id: "idle", text: "discarded" }));
    expect(statuses()).toEqual(["discarded"]);
  });

  it("closes a toast on tap", () => {
    render();
    act(() => api.show({ id: "a", text: "x" }));
    act(() => (container.querySelector('[role="status"]') as HTMLElement).click());
    expect(statuses()).toEqual([]);
  });

  it("renders the dock under the toasts while its owner is mounted", () => {
    render(<Dock node={<p>bar</p>} />);
    act(() => api.show({ id: "a", text: "toast" }));
    const viewport = container.querySelector("[data-toast-viewport]")!;
    expect(viewport.textContent).toBe("toastbar");
    render(null);
    expect(container.textContent).toBe("toast");
  });

  it("does nothing outside a provider", () => {
    act(() => root.render(<Grab />));
    expect(() => api.show({ id: "a", text: "x" })).not.toThrow();
  });
});
