/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { mount } from "@/components/Cart/testRoot";

import { Badge } from "./Badge";

describe("Badge", () => {
  let view: ReturnType<typeof mount>;

  beforeEach(() => {
    view = mount();
  });
  afterEach(() => view.unmount());

  function badge() {
    return view.container.querySelector('[role="img"]') as HTMLElement;
  }

  it("shows the number in a circle with an accessible name", () => {
    view.render(<Badge count={3} label="3 recipes" />);
    expect(badge().textContent).toBe("3");
    expect(badge().getAttribute("aria-label")).toBe("3 recipes");
    expect(badge().className).toContain("rounded-full");
    expect(badge().className).toContain("h-6");
    expect(badge().className).toContain("min-w-6");
  });

  it("has a smaller size for pinning on an icon", () => {
    view.render(<Badge count={2} label="2 recipes" size="sm" />);
    expect(badge().className).toContain("h-4");
    expect(badge().className).toContain("min-w-4");
    expect(badge().className).not.toContain("h-6");
    expect(badge().className).toContain("rounded-full");
  });

  it("caps a large number at 99+", () => {
    view.render(<Badge count={150} label="150 recipes" />);
    expect(badge().textContent).toBe("99+");
    expect(badge().getAttribute("aria-label")).toBe("150 recipes");
  });

  it("shows 99 as is", () => {
    view.render(<Badge count={99} label="99 recipes" />);
    expect(badge().textContent).toBe("99");
  });

  it("adds a caller's class", () => {
    view.render(<Badge count={1} label="1 recipe" className="ml-2" />);
    expect(badge().className).toContain("ml-2");
  });
});
