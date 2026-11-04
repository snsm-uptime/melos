// @vitest-environment jsdom

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { SearchableSelect } from "./SearchableSelect";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const OPTIONS = [
  { value: "", label: "—" },
  { value: "cup", label: "cup" },
  { value: "cucharón", label: "cucharón" },
  { value: "lata", label: "lata" },
  { value: "__other__", label: "Other…", pinned: true },
];

describe("SearchableSelect", () => {
  let host: HTMLDivElement;
  let root: Root;
  let onChange: Mock<(value: string, query: string) => void>;

  function Harness() {
    const [value, setValue] = useState("lata");
    return (
      <SearchableSelect
        aria-label="Unit"
        searchLabel="Search units"
        noResults="No unit found"
        value={value}
        options={OPTIONS}
        onChange={(next, query) => {
          setValue(next);
          onChange(next, query);
        }}
      />
    );
  }

  const trigger = () => host.querySelector("button") as HTMLButtonElement;
  const search = () => document.querySelector("input") as HTMLInputElement | null;
  const labels = () =>
    Array.from(document.querySelectorAll('[role="option"]')).map((o) => o.textContent);
  const highlighted = () => document.querySelector('[data-highlighted="true"]')?.textContent;
  const press = (key: string) =>
    act(() => {
      search()?.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    });
  function type(text: string) {
    act(() => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(
        search(),
        text,
      );
      search()?.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }

  beforeEach(() => {
    onChange = vi.fn<(value: string, query: string) => void>();
    host = document.createElement("div");
    document.body.appendChild(host);
    root = createRoot(host);
    act(() => root.render(<Harness />));
  });

  afterEach(() => {
    act(() => root.unmount());
    host.remove();
  });

  it("shows the value and opens on the option in use, with the search focused", () => {
    expect(trigger().textContent).toContain("lata");
    act(() => trigger().click());
    expect(trigger().getAttribute("aria-expanded")).toBe("true");
    expect(document.activeElement).toBe(search());
    expect(highlighted()).toBe("lata");
  });

  it("filters ignoring case and accents and keeps the pinned option", () => {
    act(() => trigger().click());
    type("CUCHARON");
    expect(labels()).toEqual(["cucharón", "Other…"]);
    expect(document.body.textContent).not.toContain("No unit found");
  });

  it("says when only the pinned option is left", () => {
    act(() => trigger().click());
    type("zzz");
    expect(labels()).toEqual(["Other…"]);
    expect(document.body.textContent).toContain("No unit found");
  });

  it("chooses the first match with Enter, passes the query and returns focus", () => {
    act(() => trigger().click());
    type(" cu ");
    press("ArrowDown");
    expect(highlighted()).toBe("cucharón");
    press("Enter");
    expect(onChange).toHaveBeenCalledWith("cucharón", "cu");
    expect(search()).toBeNull();
    expect(trigger().textContent).toContain("cucharón");
    expect(document.activeElement).toBe(trigger());
  });

  it("chooses with a click", () => {
    act(() => trigger().click());
    act(() => (document.querySelector('[role="option"]') as HTMLElement).click());
    expect(onChange).toHaveBeenCalledWith("", "");
  });

  it("closes without choosing on Escape, on an outside press and on leaving the field", () => {
    act(() => trigger().click());
    press("Escape");
    expect(search()).toBeNull();
    expect(document.activeElement).toBe(trigger());

    act(() => trigger().click());
    act(() => {
      document.body.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    });
    expect(search()).toBeNull();

    act(() => trigger().click());
    act(() => search()?.blur());
    expect(search()).toBeNull();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("does not open when disabled", () => {
    act(() =>
      root.render(
        <SearchableSelect
          aria-label="Unit"
          searchLabel="Search units"
          noResults="No unit found"
          value=""
          options={OPTIONS}
          disabled
          onChange={onChange}
        />,
      ),
    );
    act(() => trigger().click());
    expect(search()).toBeNull();
  });
});
