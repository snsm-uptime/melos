/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearCapture, openSheet } from "@/lib/capture/captureStore";

import { PictureCaptureSheet } from "./PictureCaptureSheet";

const prefs = vi.hoisted(() => ({ value: null as { locale: "en" | "es" } | null }));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));
vi.mock("@/lib/capture/captureClient", () => ({ submitPictureCapture: vi.fn() }));

const candidates = [{ id: "nb-1", name: "ana's Notebook", kind: "personal" as const, kitchenId: null }];
const notebook = { ...candidates[0], returnPath: "/notebooks/nb-1" };
const JPEG = new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 0, 0, 0, 0]);

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  URL.createObjectURL = vi.fn(() => "blob:picture");
  URL.revokeObjectURL = vi.fn();
  clearCapture();
  openSheet(notebook, "picture");
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root.render(<PictureCaptureSheet open candidates={candidates} onDraftReady={vi.fn()} />);
  });
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

function button(label: string): HTMLButtonElement | null {
  return container.querySelector(`button[aria-label="${label}"]`);
}

async function choose(file: File) {
  const input = container.querySelector('input[type="file"]:not([capture])') as HTMLInputElement;
  Object.defineProperty(input, "files", { value: [file], configurable: true });
  await act(async () => {
    input.dispatchEvent(new Event("change", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("the picture sheet's corner flow", () => {
  it("pencil opens the zoom and position editor, with save at the top-left", async () => {
    await choose(new File([JPEG], "p.jpg", { type: "image/jpeg" }));
    act(() => button("Position the picture")!.click());
    expect(container.querySelector('input[type="range"]')).not.toBeNull();
    expect(button("Save")).not.toBeNull();
    expect(button("Remove")).toBeNull();
  });

  it("trash removes the picture and brings back the upload card", async () => {
    await choose(new File([JPEG], "p.jpg", { type: "image/jpeg" }));
    act(() => button("Remove")!.click());
    expect(button("Remove")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
  });
});
