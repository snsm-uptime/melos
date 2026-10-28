/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const prefs = vi.hoisted(() => ({
  value: { locale: "es", setLanguage: vi.fn() } as {
    locale: "en" | "es";
    setLanguage: (next: "en" | "es") => Promise<void>;
  },
}));
vi.mock("@/components/PreferencesProvider", () => ({ usePreferences: () => prefs.value }));

import { LanguageChoice } from "./LanguageChoice";

describe("LanguageChoice", () => {
  let container: HTMLDivElement;
  let root: Root;
  const setLanguage = vi.fn<(next: "en" | "es") => Promise<void>>();

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    setLanguage.mockReset();
    setLanguage.mockResolvedValue(undefined);
    prefs.value = { locale: "es", setLanguage };
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  const render = () => act(() => root.render(<LanguageChoice />));
  const radio = (label: string) =>
    Array.from(container.querySelectorAll<HTMLButtonElement>("[role=radio]")).find(
      (button) => button.textContent === label,
    ) as HTMLButtonElement;

  it("shows English and Español with the current language checked", () => {
    render();
    expect(container.querySelector("[role=radiogroup]")?.getAttribute("aria-label")).toBe("Idioma");
    expect(radio("Español").getAttribute("aria-checked")).toBe("true");
    expect(radio("English").getAttribute("aria-checked")).toBe("false");
  });

  it("names the group in the interface language", () => {
    prefs.value = { locale: "en", setLanguage };
    render();
    expect(container.querySelector("[role=radiogroup]")?.getAttribute("aria-label")).toBe("Language");
    expect(radio("English").getAttribute("aria-checked")).toBe("true");
  });

  it("saves the other language once when chosen", async () => {
    render();
    await act(async () => radio("English").click());
    expect(setLanguage).toHaveBeenCalledTimes(1);
    expect(setLanguage).toHaveBeenCalledWith("en");
  });

  it("does nothing when the current language is chosen again", async () => {
    render();
    await act(async () => radio("Español").click());
    expect(setLanguage).not.toHaveBeenCalled();
  });

  it("tells the member and keeps the saved language when the save fails", async () => {
    setLanguage.mockRejectedValue(new Error("nope"));
    render();
    await act(async () => radio("English").click());
    expect(container.querySelector("[role=alert]")?.textContent).toBe(
      "No se pudo guardar el idioma. Inténtalo de nuevo.",
    );
    expect(radio("Español").getAttribute("aria-checked")).toBe("true");
    expect(radio("English").getAttribute("aria-checked")).toBe("false");
  });

  it("is disabled while a save is pending", async () => {
    let finish: () => void = () => {};
    setLanguage.mockImplementation(() => new Promise<void>((resolve) => (finish = resolve)));
    render();
    await act(async () => {
      radio("English").click();
    });
    expect(radio("English").disabled).toBe(true);
    expect(radio("Español").disabled).toBe(true);
    await act(async () => finish());
    expect(radio("English").disabled).toBe(false);
  });

  it("moves with the arrow keys", async () => {
    render();
    await act(async () => {
      radio("Español").dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    });
    expect(setLanguage).toHaveBeenCalledWith("en");
  });
});
