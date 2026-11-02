/** @vitest-environment jsdom */

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { startCartEdit } = vi.hoisted(() => ({ startCartEdit: vi.fn() }));
vi.mock("@/lib/cartClient", () => ({ startCartEdit }));

import { CartEditingBar, EDITING_NOTICE_MS } from "./CartEditingBar";
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
    startCartEdit.mockReset().mockResolvedValue({ ok: true, value: {} });
  });
  afterEach(() => {
    view.unmount();
    vi.useRealTimers();
  });

  function render() {
    view.render(
      <CartEditingBar
        kitchenId="k1"
        idleExpiresAt={new Date(START + 5 * 60_000).toISOString()}
        locale="en"
        onChanged={onChanged}
      />,
    );
  }

  const dismiss = () =>
    view.container.querySelector<HTMLButtonElement>('button[aria-label="Dismiss"]');

  it("says I'm editing, with only a dismiss button", () => {
    render();
    const status = view.container.querySelector('[role="status"]');
    expect(status?.textContent).toContain(
      "You're editing the cart. Others can't change it until you save or discard.",
    );
    expect(view.container.querySelector("a")).toBeNull();
    expect(view.container.querySelectorAll("button")).toHaveLength(1);
    expect(dismiss()).not.toBeNull();
  });

  it("closes when dismissed", () => {
    render();
    act(() => dismiss()?.click());
    expect(view.container.textContent).toBe("");
  });

  it("closes on its own after 30 seconds", () => {
    render();
    act(() => vi.advanceTimersByTime(EDITING_NOTICE_MS - 1));
    expect(view.container.textContent).toContain("You're editing the cart.");
    act(() => vi.advanceTimersByTime(1));
    expect(view.container.textContent).toBe("");
  });

  it("still warns before the idle limit after the notice has closed", () => {
    render();
    act(() => dismiss()?.click());
    act(() => vi.advanceTimersByTime(4 * 60_000));
    expect(view.container.textContent).toContain(
      "Your cart changes will be discarded in 1 minute",
    );
  });

  it("does not auto-close the warning, but dismissing does", () => {
    render();
    act(() => vi.advanceTimersByTime(4 * 60_000));
    act(() => vi.advanceTimersByTime(EDITING_NOTICE_MS));
    expect(view.container.textContent).toContain("Keep editing");
    act(() => dismiss()?.click());
    expect(view.container.textContent).toBe("");
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
