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

/** The options a SearchableSelect offers; it is left closed. */
function choices(trigger: string): string[] {
  const button = document.querySelector(trigger) as HTMLButtonElement;
  act(() => button.click());
  const labels = Array.from(document.querySelectorAll('[role="option"]')).map(
    (option) => option.textContent ?? "",
  );
  act(() => button.click());
  return labels;
}

/** Opens a SearchableSelect and chooses the option labelled `label`. */
function pick(trigger: string, label: string) {
  act(() => (document.querySelector(trigger) as HTMLButtonElement).click());
  const option = Array.from(document.querySelectorAll<HTMLElement>('[role="option"]')).find(
    (item) => item.textContent === label,
  );
  act(() => option!.click());
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

  it("sends an optional place, offering my own places and the defaults (spec 070)", async () => {
    client.addShoppingItem.mockResolvedValue({ ok: true, value: {} });
    view.render(
      <HandItems
        kitchenId="k1"
        locale="en"
        items={[]}
        readOnly={false}
        onChange={onChange}
        customPlaces={[{ id: "p1", name: "Asian market" }]}
      />,
    );
    const picker = 'button[aria-label="Where to buy (optional)"]';
    expect(choices(picker)).toEqual([
      "Choose later",
      // Own places A to Z, a divider, then the defaults A to Z.
      "Asian market",
      "Bakery",
      "Butcher",
      "Farmers market",
      "Fish market",
      "Other",
      "Pharmacy or drugstore",
      "Supermarket",
    ]);
    act(() => (document.querySelector(picker) as HTMLButtonElement).click());
    const divider = document.querySelector('[role="separator"]');
    expect(divider?.previousElementSibling?.textContent).toBe("Asian market");
    act(() => (document.querySelector(picker) as HTMLButtonElement).click());
    type(view.container.querySelector("input") as HTMLInputElement, "Dish soap");
    pick(picker, "Pharmacy or drugstore");
    expect(view.container.querySelector(picker)?.textContent).toBe("Pharmacy or drugstore");
    await submit(view.container.querySelector("form") as HTMLFormElement);
    expect(client.addShoppingItem).toHaveBeenCalledWith("k1", {
      name: "Dish soap",
      place: { kind: "default", key: "pharmacy" },
    });
  });

  it("toggles bought on an item added by hand", () => {
    const onToggle = vi.fn();
    view.render(
      <HandItems
        kitchenId="k1"
        locale="en"
        items={[SOAP]}
        readOnly={false}
        onChange={onChange}
        onToggle={onToggle}
      />,
    );
    act(() => (view.container.querySelector('input[type="checkbox"]') as HTMLElement).click());
    expect(onToggle).toHaveBeenCalledWith("i1", true);
  });

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

  it("sends the unit chosen in the searchable unit picker", async () => {
    client.addShoppingItem.mockResolvedValue({ ok: true, value: {} });
    render();
    const unit = 'button[aria-label="Unit"]';
    expect(view.container.querySelector(unit)?.textContent).toBe("No unit");
    const [name, quantity] = Array.from(view.container.querySelectorAll("input"));
    type(name, "Flour");
    type(quantity, "2");
    pick(unit, "kg");
    await submit(view.container.querySelector("form") as HTMLFormElement);

    expect(client.addShoppingItem).toHaveBeenCalledWith("k1", {
      name: "Flour",
      quantity: "2",
      unit: "kg",
    });
    expect(view.container.querySelector(unit)?.textContent).toBe("No unit");
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
