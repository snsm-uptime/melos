/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it, vi } from "vitest";

import { useLocale } from "./useLocale";

const prefs = vi.hoisted(() => ({ value: null as { locale: "en" | "es" } | null }));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));

function Probe() {
  return <span>{useLocale()}</span>;
}

function render(): string {
  const container = document.createElement("div");
  const root = createRoot(container);
  act(() => root.render(<Probe />));
  const text = container.textContent ?? "";
  act(() => root.unmount());
  return text;
}

describe("useLocale", () => {
  it("is en without a provider (component tests)", () => {
    prefs.value = null;
    expect(render()).toBe("en");
  });

  it("is the provider's locale inside one", () => {
    prefs.value = { locale: "es" };
    expect(render()).toBe("es");
    prefs.value = { locale: "en" };
    expect(render()).toBe("en");
  });
});
