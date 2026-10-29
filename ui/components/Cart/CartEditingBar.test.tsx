/** @vitest-environment jsdom */

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { discardCart, startCartEdit } = vi.hoisted(() => ({
  discardCart: vi.fn(),
  startCartEdit: vi.fn(),
}));
vi.mock("@/lib/cartClient", () => ({ discardCart, startCartEdit }));

import { CartEditingBar } from "./CartEditingBar";
import { mount } from "./testRoot";

const START = new Date("2026-10-29T12:00:00Z").getTime();

describe("CartEditingBar", () => {
  let view: ReturnType<typeof mount>;
  const onChanged = vi.fn();

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(START);
    view = mount();
    onChanged.mockReset();
    discardCart.mockReset().mockResolvedValue({ ok: true, value: true });
    startCartEdit.mockReset().mockResolvedValue({ ok: true, value: {} });
  });
  afterEach(() => {
    view.unmount();
    vi.useRealTimers();
  });

  const onSave = vi.fn();

  function render() {
    view.render(
      <CartEditingBar
        kitchenId="k1"
        idleExpiresAt={new Date(START + 5 * 60_000).toISOString()}
        locale="en"
        onChanged={onChanged}
        onSave={onSave}
      />,
    );
  }

  it("says I'm editing and offers Save and Discard, with no link", async () => {
    render();
    const status = view.container.querySelector('[role="status"]');
    expect(status?.textContent).toContain(
      "You're editing the cart. Others can't change it until you save or discard.",
    );
    expect(view.container.querySelector("a")).toBeNull();
    const save = Array.from(view.container.querySelectorAll("button")).find(
      (b) => b.textContent === "Save",
    );
    act(() => save?.click());
    expect(onSave).toHaveBeenCalled();
    const discard = Array.from(view.container.querySelectorAll("button")).find(
      (b) => b.textContent === "Discard",
    );
    await act(async () => discard?.click());
    expect(discardCart).toHaveBeenCalledWith("k1");
    expect(onChanged).toHaveBeenCalled();
  });

  it("warns a minute before the end, keeps editing, and says when discarded", async () => {
    render();
    act(() => vi.advanceTimersByTime(4 * 60_000));
    expect(view.container.textContent).toContain(
      "Your cart changes will be discarded in 1 minute",
    );
    const keep = Array.from(view.container.querySelectorAll("button")).find(
      (b) => b.textContent === "Keep editing",
    );
    await act(async () => keep?.click());
    expect(startCartEdit).toHaveBeenCalledWith("k1");
    act(() => vi.advanceTimersByTime(60_000));
    expect(view.container.textContent).toContain("Your cart changes were discarded");
    expect(onChanged).toHaveBeenCalled();
  });
});
