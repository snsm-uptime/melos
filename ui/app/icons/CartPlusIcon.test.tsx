/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { CartPlusIcon } from "./CartPlusIcon";

describe("CartPlusIcon", () => {
  let container: HTMLDivElement;
  let root: Root;
  beforeEach(() => {
    container = document.createElement("div");
    root = createRoot(container);
  });
  afterEach(() => act(() => root.unmount()));

  const mark = () => container.querySelector<SVGGElement>("[data-testid=cart-plus-mark]")!;

  it("is one hidden svg with an upright plus", () => {
    act(() => root.render(<CartPlusIcon />));
    expect(container.querySelectorAll("svg")).toHaveLength(1);
    expect(container.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
    expect(mark().style.transform).toBe("none");
  });

  it("turns the plus 45° into an × when in the cart", () => {
    act(() => root.render(<CartPlusIcon inCart />));
    expect(mark().style.transform).toBe("rotate(45deg)");
  });
});
