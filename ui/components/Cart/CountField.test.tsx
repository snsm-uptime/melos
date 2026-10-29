/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CountField } from "./CountField";
import { mount, type } from "./testRoot";

describe("CountField", () => {
  let view: ReturnType<typeof mount>;
  beforeEach(() => {
    view = mount();
  });
  afterEach(() => view.unmount());

  it("is labelled and sends a valid whole number", () => {
    const onChange = vi.fn();
    view.render(<CountField label="Meals" value={1} onChange={onChange} locale="en" />);
    const input = view.container.querySelector("input")!;
    expect(view.container.querySelector(`label[for="${input.id}"]`)?.textContent).toBe("Meals");
    type(input, "3");
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it.each(["0", "100", "1.5", ""])("keeps the last valid value for %j and says why", (text) => {
    const onChange = vi.fn();
    view.render(<CountField label="People" value={2} onChange={onChange} locale="en" />);
    type(view.container.querySelector("input")!, text);
    expect(onChange).not.toHaveBeenCalled();
    expect(view.container.querySelector('[role="alert"]')?.textContent).toBe(
      "Enter a whole number from 1 to 99",
    );
  });

  it("speaks Spanish", () => {
    view.render(<CountField label="Personas" value={2} onChange={vi.fn()} locale="es" />);
    type(view.container.querySelector("input")!, "x");
    expect(view.container.textContent).toContain("Escribe un número entero del 1 al 99");
  });
});
