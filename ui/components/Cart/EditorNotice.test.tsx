/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { EditorNotice } from "./EditorNotice";
import { mount } from "./testRoot";

describe("EditorNotice", () => {
  let view: ReturnType<typeof mount>;
  beforeEach(() => {
    view = mount();
  });
  afterEach(() => view.unmount());

  it("names the cart editor", () => {
    view.render(<EditorNotice alias="ana" kind="cart" locale="en" />);
    const status = view.container.querySelector('[role="status"]');
    expect(status?.textContent).toBe("ana is editing the cart");
  });

  it("reads unknown without an alias, and names the recipe editor in Spanish", () => {
    view.render(<EditorNotice alias={null} kind="recipe" locale="es" />);
    expect(view.container.textContent).toBe("desconocido está editando esta receta");
  });
});
