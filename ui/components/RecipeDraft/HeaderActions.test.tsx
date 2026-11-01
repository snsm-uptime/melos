/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { CauldronLoader } from "@/components/CauldronLoader";
import { mount } from "@/components/Cart/testRoot";

import { HeaderAction } from "./HeaderActions";

describe("HeaderAction", () => {
  let view: ReturnType<typeof mount>;

  beforeEach(() => {
    view = mount();
  });
  afterEach(() => view.unmount());

  const button = () => view.container.querySelector("button") as HTMLButtonElement;

  it("dims a disabled action", () => {
    view.render(<HeaderAction label="Save" icon={<span />} tone="accent" disabled onClick={() => {}} />);
    expect(button().className).toContain("disabled:opacity-50");
    expect(button().hasAttribute("aria-busy")).toBe(false);
  });

  it("keeps a busy action at full colour, disabled and marked busy", () => {
    view.render(
      <HeaderAction
        label="Saving"
        icon={<CauldronLoader tone="button" size="1.25rem" label="Saving" />}
        tone="accent"
        disabled
        busy
        onClick={() => {}}
      />,
    );
    expect(button().disabled).toBe(true);
    expect(button().getAttribute("aria-busy")).toBe("true");
    expect(button().className).not.toContain("disabled:opacity-50");
    expect(button().className).not.toContain("disabled:text-muted");
    expect(button().getAttribute("aria-label")).toBe("Saving");
    expect(button().querySelector("[role='status']")).toBeNull();
  });
});
