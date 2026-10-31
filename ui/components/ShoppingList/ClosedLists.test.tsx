/** @vitest-environment jsdom */

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { client } = vi.hoisted(() => ({
  client: { fetchClosedLists: vi.fn(), fetchClosedList: vi.fn() },
}));
vi.mock("@/lib/shoppingListClient", () => client);

import { mount } from "@/components/Cart/testRoot";

import { ClosedListDetail, ClosedLists, formatClosingDate } from "./ClosedLists";

async function settle() {
  await act(async () => {
    await Promise.resolve();
  });
}

describe("closed lists", () => {
  let view: ReturnType<typeof mount>;

  beforeEach(() => {
    view = mount();
    client.fetchClosedLists.mockReset();
    client.fetchClosedList.mockReset();
  });
  afterEach(() => view.unmount());

  it("formats a date with no day shift", () => {
    expect(formatClosingDate("2026-10-30", "en")).toBe("October 30, 2026");
    expect(formatClosingDate("2026-10-30", "es")).toContain("30");
  });

  it("lists closed lists with links", async () => {
    client.fetchClosedLists.mockResolvedValue({
      ok: true,
      value: [{ id: "l1", closing_date: "2026-10-30", recipe_titles: ["Rice", "Bread"] }],
    });
    view.render(<ClosedLists kitchenId="k1" locale="en" />);
    await settle();

    expect(view.container.textContent).toContain("Closed on October 30, 2026");
    expect(view.container.textContent).toContain("Rice, Bread");
    expect(view.container.querySelector('a[href="/kitchens/k1/shopping-lists/l1"]')).not.toBeNull();
  });

  it("says so when there are none, and on an error", async () => {
    client.fetchClosedLists.mockResolvedValue({ ok: true, value: [] });
    view.render(<ClosedLists kitchenId="k1" locale="en" />);
    await settle();
    expect(view.container.textContent).toContain("No closed lists yet.");

    client.fetchClosedLists.mockResolvedValue({ ok: false, status: 404, code: null });
    view.render(<ClosedLists kitchenId="k2" locale="en" />);
    await settle();
    expect(view.container.querySelector('[role="alert"]')).not.toBeNull();
  });

  it("shows a list as saved with no controls, in Spanish too", async () => {
    client.fetchClosedList.mockResolvedValue({
      ok: true,
      value: {
        id: "l1",
        closing_date: "2026-10-30",
        lines: [],
        your_call: [],
        hand_items: [{ id: "i", name: "jabón", quantity: null, unit: null, size: null }],
      },
    });
    view.render(<ClosedListDetail kitchenId="k1" listId="l1" locale="es" />);
    await settle();

    expect(view.container.textContent).toContain("Cerrada el");
    expect(view.container.textContent).toContain("jabón");
    expect(view.container.querySelector("button")).toBeNull();
  });
});
