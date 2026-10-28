/** @vitest-environment jsdom */

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ServingsControl } from "./ServingsControl";

function setValue(element: HTMLInputElement, value: string) {
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
}

describe("ServingsControl", () => {
  let container: HTMLDivElement;
  let root: Root;
  const onChange = vi.fn();

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    onChange.mockReset();
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  /** A parent that applies what the control reports, like the detail view does. */
  function Harness({ start, locale = "en" }: { start: number; locale?: "en" | "es" }) {
    const [value, setValue] = useState(start);
    return (
      <ServingsControl
        value={value}
        locale={locale}
        onChange={(next) => {
          onChange(next);
          setValue(next);
        }}
      />
    );
  }

  function render(start = 4, locale: "en" | "es" = "en") {
    act(() => root.render(<Harness start={start} locale={locale} />));
  }

  const input = () => container.querySelector("input") as HTMLInputElement;
  const button = (label: string) =>
    container.querySelector(`button[aria-label="${label}"]`) as HTMLButtonElement;
  const hint = () => container.querySelector("[role=alert]");
  const live = () => container.querySelector("[aria-live=polite]")?.textContent;

  it("starts at the given servings with a label and an empty announcement", () => {
    render(4);
    expect(input().value).toBe("4");
    expect(container.querySelector("label")?.textContent).toBe("Servings");
    expect(container.querySelector(`label[for="${input().id}"]`)).not.toBeNull();
    expect(live()).toBe("");
    expect(hint()).toBeNull();
  });

  it("applies a valid typed number at once and announces it", () => {
    render(4);
    act(() => setValue(input(), "6"));
    expect(onChange).toHaveBeenCalledWith(6);
    expect(input().value).toBe("6");
    expect(live()).toBe("Amounts for 6 servings");
  });

  it("never shows the hint for a valid prefix on the way to a longer number", () => {
    render(4);
    act(() => setValue(input(), "1"));
    expect(hint()).toBeNull();
    act(() => setValue(input(), "12"));
    expect(hint()).toBeNull();
    expect(onChange.mock.calls.map((call) => call[0])).toEqual([1, 12]);
  });

  it.each(["abc", "0", "101", "2.5", ""])("does not apply %j and shows the hint", (text) => {
    render(4);
    act(() => setValue(input(), text));
    expect(onChange).not.toHaveBeenCalled();
    expect(hint()?.textContent).toBe("Enter a whole number from 1 to 100.");
    expect(input().value).toBe(text);
  });

  it("restores the applied value and hides the hint on blur", () => {
    render(4);
    act(() => setValue(input(), "abc"));
    act(() => {
      input().dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
    });
    expect(input().value).toBe("4");
    expect(hint()).toBeNull();
  });

  it("restores the applied value on Enter", () => {
    render(4);
    act(() => setValue(input(), "999"));
    act(() => {
      input().dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    });
    expect(input().value).toBe("4");
    expect(hint()).toBeNull();
  });

  it("steps with the buttons", () => {
    render(4);
    act(() => button("More servings").click());
    act(() => button("Fewer servings").click());
    act(() => button("Fewer servings").click());
    expect(onChange.mock.calls.map((call) => call[0])).toEqual([5, 4, 3]);
    expect(input().value).toBe("3");
  });

  it("disables Fewer at 1 and More at 100", () => {
    render(1);
    expect(button("Fewer servings").disabled).toBe(true);
    expect(button("More servings").disabled).toBe(false);
    act(() => root.unmount());
    root = createRoot(container);
    render(100);
    expect(button("More servings").disabled).toBe(true);
    expect(button("Fewer servings").disabled).toBe(false);
  });

  it("steps down from a recipe saved above 100 to 100", () => {
    render(120);
    expect(button("More servings").disabled).toBe(true);
    act(() => button("Fewer servings").click());
    expect(onChange).toHaveBeenCalledWith(100);
  });

  it("speaks Spanish when asked", () => {
    render(4, "es");
    expect(container.querySelector("label")?.textContent).toBe("Porciones");
    act(() => button("Más porciones").click());
    expect(live()).toBe("Cantidades para 5 porciones");
  });

  it("follows the value when it is changed from outside after a typed entry", () => {
    function Outside() {
      const [value, setValue] = useState(4);
      return (
        <>
          <ServingsControl value={value} locale="en" onChange={setValue} />
          <button type="button" id="outside" onClick={() => setValue(4)}>
            back
          </button>
        </>
      );
    }
    act(() => root.render(<Outside />));
    act(() => setValue(input(), "7"));
    expect(input().value).toBe("7");
    act(() => (container.querySelector("#outside") as HTMLButtonElement).click());
    expect(input().value).toBe("4");
  });
});
