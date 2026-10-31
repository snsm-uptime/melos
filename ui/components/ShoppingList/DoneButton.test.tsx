/** @vitest-environment jsdom */

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { client } = vi.hoisted(() => ({ client: { closeShoppingList: vi.fn() } }));
vi.mock("@/lib/shoppingListClient", () => client);

import { mount } from "@/components/Cart/testRoot";

import { DoneButton } from "./DoneButton";

function button(text: string): HTMLButtonElement {
  const found = Array.from(document.querySelectorAll("button")).filter(
    (b) => b.textContent === text,
  );
  return found[found.length - 1] as HTMLButtonElement;
}

describe("DoneButton", () => {
  let view: ReturnType<typeof mount>;
  const onClosed = vi.fn();

  beforeEach(() => {
    view = mount();
    onClosed.mockReset();
    client.closeShoppingList.mockReset();
  });
  afterEach(() => view.unmount());

  function render(over: { empty?: boolean; editing?: boolean; locale?: "en" | "es" } = {}) {
    view.render(
      <DoneButton
        kitchenId="k1"
        listId="l1"
        locale={over.locale ?? "en"}
        empty={over.empty ?? false}
        editing={over.editing ?? false}
        onClosed={onClosed}
      />,
    );
  }

  it("closes only after confirming", async () => {
    client.closeShoppingList.mockResolvedValue({ ok: true, value: {} });
    render();
    act(() => button("Done").click());
    expect(client.closeShoppingList).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain("Close this list?");

    await act(async () => {
      button("Done").click();
      await Promise.resolve();
    });
    expect(client.closeShoppingList).toHaveBeenCalledWith("k1", "l1");
    expect(onClosed).toHaveBeenCalled();
  });

  it("reads Listo in Spanish", () => {
    render({ locale: "es" });
    expect(button("Listo")).toBeDefined();
  });

  it("is disabled for an empty list and while I edit the cart", () => {
    render({ empty: true });
    expect(button("Done").disabled).toBe(true);
    expect(view.container.textContent).toContain("Add something to the list first.");
    render({ editing: true });
    expect(button("Done").disabled).toBe(true);
    expect(view.container.textContent).toContain("Save or discard your cart changes first.");
  });

  it("refreshes when someone else closed it first", async () => {
    client.closeShoppingList.mockResolvedValue({
      ok: false,
      status: 409,
      code: "list_not_active",
    });
    render();
    act(() => button("Done").click());
    await act(async () => {
      button("Done").click();
      await Promise.resolve();
    });
    expect(onClosed).toHaveBeenCalled();
  });
});
