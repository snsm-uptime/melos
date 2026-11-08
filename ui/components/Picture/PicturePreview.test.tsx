/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PicturePreview } from "./PicturePreview";

const prefs = vi.hoisted(() => ({ value: null as { locale: "en" | "es" } | null }));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));

const SRC = "data:image/webp;base64,UklGRg==";

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  prefs.value = null;
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

function render(open: boolean, onClose = vi.fn()) {
  act(() => root.render(<PicturePreview open={open} src={SRC} title="Soup" onClose={onClose} />));
  return onClose;
}

describe("PicturePreview", () => {
  it("shows the stored picture when open", () => {
    render(true);
    const image = document.querySelector("img");
    expect(image?.getAttribute("src")).toBe(SRC);
    expect(image?.getAttribute("alt")).toBe("The chosen picture");
  });

  it("offers no download link and no other image", () => {
    render(true);
    expect(document.querySelector("a[download]")).toBeNull();
    expect(document.querySelectorAll("img")).toHaveLength(1);
  });

  it("closes on Escape", () => {
    const onClose = render(true);
    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });
    expect(onClose).toHaveBeenCalled();
  });

  it("is not shown when closed", () => {
    render(false);
    expect(document.querySelector("img")).toBeNull();
  });

  it("labels its close control in Spanish under the Spanish locale", () => {
    prefs.value = { locale: "es" };
    render(true);
    expect(document.querySelector('[aria-label="Cerrar"]')).not.toBeNull();
  });
});
