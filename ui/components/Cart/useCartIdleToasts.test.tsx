/** @vitest-environment jsdom */

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { startCartEdit } = vi.hoisted(() => ({ startCartEdit: vi.fn() }));
vi.mock("@/lib/cartClient", () => ({ startCartEdit }));

import { ToastProvider, ToastViewport } from "@/components/Toast";
import type { CartEditor } from "@/lib/cartClient";

import { mount } from "./testRoot";
import { useCartIdleToasts } from "./useCartIdleToasts";

const START = new Date("2026-10-29T12:00:00Z").getTime();
const MINE: CartEditor = {
  alias: "ana",
  is_me: true,
  idle_expires_at: new Date(START + 5 * 60_000).toISOString(),
};

function Probe({ editor, onChanged }: { editor: CartEditor | null; onChanged: () => void }) {
  useCartIdleToasts("k1", editor, "en", onChanged);
  return null;
}

describe("useCartIdleToasts", () => {
  let view: ReturnType<typeof mount>;
  const onChanged = vi.fn();

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(START);
    view = mount();
    onChanged.mockReset();
    startCartEdit.mockReset().mockResolvedValue({ ok: true, value: {} });
  });
  afterEach(() => {
    view.unmount();
    vi.useRealTimers();
  });

  function render(editor: CartEditor | null) {
    view.render(
      <ToastProvider>
        <Probe editor={editor} onChanged={onChanged} />
        <ToastViewport />
      </ToastProvider>,
    );
  }
  const toastText = () => view.container.querySelector("[data-toast-viewport]")?.textContent ?? "";

  it("warns at 4 minutes with Keep editing, then says the changes were discarded", async () => {
    render(MINE);
    act(() => vi.advanceTimersByTime(3 * 60_000));
    expect(toastText()).toBe("");
    act(() => vi.advanceTimersByTime(60_000));
    expect(toastText()).toBe("Your cart changes will be discarded in 1 minuteKeep editing");
    await act(async () => view.container.querySelector("button")?.click());
    expect(startCartEdit).toHaveBeenCalledWith("k1");
    act(() => vi.advanceTimersByTime(60_000));
    expect(toastText()).toBe("Your cart changes were discarded");
    expect(onChanged).toHaveBeenCalled();
    const calls = onChanged.mock.calls.length;
    act(() => vi.advanceTimersByTime(2_000));
    expect(onChanged.mock.calls.length).toBe(calls);
  });

  it("shows nothing when the lock is someone else's", () => {
    render({ alias: "ben", is_me: false, idle_expires_at: null });
    act(() => vi.advanceTimersByTime(6 * 60_000));
    expect(toastText()).toBe("");
  });
});
