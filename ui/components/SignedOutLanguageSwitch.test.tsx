/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const prefs = vi.hoisted(() => ({ locale: "es" as "en" | "es", setLanguage: vi.fn() }));
vi.mock("@/components/PreferencesProvider", () => ({ usePreferences: () => prefs }));

import { SignedOutLanguageSwitch } from "./SignedOutLanguageSwitch";

describe("SignedOutLanguageSwitch", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    prefs.setLanguage.mockReset();
    prefs.locale = "es";
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  const render = () => act(() => root.render(<SignedOutLanguageSwitch />));
  const button = (label: string) =>
    Array.from(container.querySelectorAll("button")).find((b) => b.textContent === label) as HTMLButtonElement;

  it("floats in the corner by default and sits in its column when inline", () => {
    render();
    const corner = container.querySelector("[role=group]") as HTMLElement;
    expect(corner.className).toContain("absolute");
    // Inset from the right edge by the standard page gutter, not a one-off value.
    expect(corner.className).toContain("right-[max(var(--page-gutter),env(safe-area-inset-right))]");

    act(() => root.render(<SignedOutLanguageSwitch placement="inline" />));
    const group = container.querySelector("[role=group]") as HTMLElement;
    expect(group.className).not.toContain("absolute");
    expect(button("English")).toBeTruthy();
  });

  it("marks the current language as pressed", () => {
    render();
    expect(button("Español").getAttribute("aria-pressed")).toBe("true");
    expect(button("English").getAttribute("aria-pressed")).toBe("false");
    expect(container.querySelector("[role=group]")?.getAttribute("aria-label")).toBe("Idioma");
  });

  it("applies the other language once when it is pressed", () => {
    render();
    act(() => button("English").click());
    expect(prefs.setLanguage).toHaveBeenCalledTimes(1);
    expect(prefs.setLanguage).toHaveBeenCalledWith("en");
  });

  it("does nothing when the current language is pressed", () => {
    render();
    act(() => button("Español").click());
    expect(prefs.setLanguage).not.toHaveBeenCalled();
  });

  it("reads the same labels in both languages", () => {
    prefs.locale = "en";
    render();
    expect(button("English").getAttribute("aria-pressed")).toBe("true");
    expect(container.querySelector("[role=group]")?.getAttribute("aria-label")).toBe("Language");
    expect(container.textContent).toBe("EnglishEspañol");
  });
});
