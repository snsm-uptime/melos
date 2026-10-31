/** @vitest-environment jsdom */

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { client } = vi.hoisted(() => ({
  client: { addShoppingItem: vi.fn(), removeShoppingItem: vi.fn() },
}));
vi.mock("@/lib/shoppingListClient", () => client);

import { mount } from "@/components/Cart/testRoot";

import { HandItems } from "./HandItems";

const SOAP = { id: "i1", name: "soap", quantity: null, unit: null, size: null };

function type(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  act(() => {
    setter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function submit(form: HTMLFormElement) {
  await act(async () => {
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await Promise.resolve();
  });
}

describe("HandItems", () => {
  let view: ReturnType<typeof mount>;
  const onChange = vi.fn();

  beforeEach(() => {
    view = mount();
    onChange.mockReset();
    client.addShoppingItem.mockReset();
    client.removeShoppingItem.mockReset();
  });
  afterEach(() => view.unmount());

  function render(readOnly = false) {
    view.render(
      <HandItems kitchenId="k1" locale="en" items={[SOAP]} readOnly={readOnly} onChange={onChange} />,
    );
  }

  it("adds an item with only a name and clears the form", async () => {
    client.addShoppingItem.mockResolvedValue({ ok: true, value: { is_empty: false } });
    render();
    const name = view.container.querySelector("input") as HTMLInputElement;
    type(name, "Milk");
    await submit(view.container.querySelector("form") as HTMLFormElement);

    expect(client.addShoppingItem).toHaveBeenCalledWith("k1", { name: "Milk" });
    expect(onChange).toHaveBeenCalled();
    expect(name.value).toBe("");
  });

  it("defaults an amount with no unit to a count", async () => {
    client.addShoppingItem.mockResolvedValue({ ok: true, value: {} });
    render();
    const [name, quantity] = Array.from(view.container.querySelectorAll("input"));
    type(name, "Milk");
    type(quantity, "2");
    await submit(view.container.querySelector("form") as HTMLFormElement);

    expect(client.addShoppingItem).toHaveBeenCalledWith("k1", {
      name: "Milk",
      quantity: "2",
      unit: "unit",
    });
  });

  it("shows a plain message for a refused item and keeps the text", async () => {
    client.addShoppingItem.mockResolvedValue({ ok: false, status: 422, code: "invalid_item" });
    render();
    const name = view.container.querySelector("input") as HTMLInputElement;
    type(name, "Milk");
    await submit(view.container.querySelector("form") as HTMLFormElement);

    expect(view.container.querySelector('[role="alert"]')?.textContent).toBe(
      "Check the item's name and amount.",
    );
    expect(name.value).toBe("Milk");
  });

  it("removes an item", async () => {
    client.removeShoppingItem.mockResolvedValue({ ok: true, value: {} });
    render();
    const remove = view.container.querySelector('[aria-label="Remove soap"]') as HTMLElement;
    await act(async () => {
      remove.click();
      await Promise.resolve();
    });
    expect(client.removeShoppingItem).toHaveBeenCalledWith("k1", "i1");
    expect(onChange).toHaveBeenCalled();
  });

  it("is read only in an archived kitchen", () => {
    render(true);
    expect(view.container.querySelector("form")).toBeNull();
    expect(view.container.querySelector("button")).toBeNull();
    expect(view.container.textContent).toContain("soap");
  });
});
