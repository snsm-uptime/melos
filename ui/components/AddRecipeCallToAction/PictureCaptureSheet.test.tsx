/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearCapture, getCaptureState, openSheet } from "@/lib/capture/captureStore";

import { PictureCaptureSheet } from "./PictureCaptureSheet";

const prefs = vi.hoisted(() => ({ value: null as { locale: "en" | "es" } | null }));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

const submit = vi.hoisted(() => vi.fn());
vi.mock("@/lib/capture/captureClient", () => ({ submitPictureCapture: submit }));

const candidates = [
  { id: "nb-1", name: "ana's Notebook", kind: "personal" as const, kitchenId: null },
];
const notebook = { ...candidates[0], returnPath: "/notebooks/nb-1" };

const draftResponse = {
  outcome: "draft",
  notebook: { id: "nb-1", kind: "personal", name: "ana's Notebook", kitchen_id: null },
  language: "en",
  catalog: [],
  draft: {
    title: "Tomato soup",
    base_servings: 4,
    servings_estimated: false,
    changes: [],
    ingredient_lines: [],
    steps: ["Blend."],
  },
  picture: {
    tier: "tier_3",
    sharpness: null,
    original_dimensions: [64, 48],
    final_dimensions: [64, 48],
    size_kb: 1,
    steps_taken: [],
    preview_image: "data:image/webp;base64,UklGRg==",
  },
};

const JPEG = new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 0, 0, 0, 0]);
const PDF = new TextEncoder().encode("%PDF-1.7\n");

let container: HTMLDivElement;
let root: Root;
const onDraftReady = vi.fn();

beforeEach(() => {
  prefs.value = null;
  submit.mockReset();
  onDraftReady.mockReset();
  vi.stubGlobal("URL", Object.assign(URL, {
    createObjectURL: vi.fn(() => "blob:picture"),
    revokeObjectURL: vi.fn(),
  }));
  clearCapture();
  openSheet(notebook, "picture");
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root.render(
      <PictureCaptureSheet open candidates={candidates} onDraftReady={onDraftReady} />,
    );
  });
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

function input(): HTMLInputElement {
  // The gallery and file input; the camera input is the one with a capture attribute.
  return container.querySelector('input[type="file"]:not([capture])') as HTMLInputElement;
}

async function choose(files: File[]) {
  Object.defineProperty(input(), "files", { value: files, configurable: true });
  await act(async () => {
    input().dispatchEvent(new Event("change", { bubbles: true }));
  });
  // The check reads the bytes asynchronously; let it finish.
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

function keptFile(): File | null | undefined {
  const source = getCaptureState().source;
  return source.kind === "picture" ? source.file : undefined;
}

function button(label: string): HTMLButtonElement | null {
  return Array.from(container.querySelectorAll("button")).find(
    (b) => b.getAttribute("aria-label") === label || b.textContent?.trim() === label,
  ) as HTMLButtonElement | null;
}

function handwrittenSwitch(): HTMLButtonElement | null {
  return container.querySelector('button[role="switch"]');
}

function submitButton(): HTMLButtonElement {
  return container.querySelector('button[type="submit"]') as HTMLButtonElement;
}

describe("PictureCaptureSheet", () => {
  it("shows the Handwritten switch on by default", () => {
    const toggle = handwrittenSwitch();
    expect(toggle?.getAttribute("role")).toBe("switch");
    expect(toggle?.getAttribute("aria-checked")).toBe("true");
  });

  it("the switch sends handwritten false when turned off, and keeps the file", async () => {
    await choose([new File([JPEG], "p.jpg", { type: "image/jpeg" })]);
    act(() => handwrittenSwitch()?.click());
    expect(getCaptureState().source).toMatchObject({ handwritten: false });
    expect(getCaptureState().source).toMatchObject({ kind: "picture" });
    expect(keptFile()).not.toBeNull();
  });

  it("the submit control is disabled with no file", () => {
    expect(submitButton().disabled).toBe(true);
  });

  it("has an input for JPEG, PNG and HEIC with no capture attribute", () => {
    expect(input().getAttribute("accept")).toContain("image/jpeg");
    expect(input().getAttribute("accept")).toContain(".heic");
    expect(input().hasAttribute("capture")).toBe(false);
  });

  it("a chosen JPEG is kept and enables Read recipe", async () => {
    await choose([new File([JPEG], "p.jpg", { type: "image/jpeg" })]);
    expect(keptFile()?.name).toBe(
      "p.jpg",
    );
    expect(submitButton().disabled).toBe(false);
  });

  it("a PDF is refused with a message and the previous choice stays", async () => {
    await choose([new File([JPEG], "first.jpg", { type: "image/jpeg" })]);
    await choose([new File([PDF], "a.jpg", { type: "image/jpeg" })]);
    expect(container.textContent).toContain("That file isn't a supported picture");
    expect(keptFile()?.name).toBe(
      "first.jpg",
    );
  });

  it("two files at once choose neither and show the one-at-a-time message", async () => {
    await choose([
      new File([JPEG], "a.jpg", { type: "image/jpeg" }),
      new File([JPEG], "b.jpg", { type: "image/jpeg" }),
    ]);
    expect(container.textContent).toContain("Choose one picture at a time.");
    expect(keptFile()).toBeNull();
  });

  it("submit sends the notebook, the file and the switch, then shows the draft", async () => {
    submit.mockResolvedValue({ ok: true, value: draftResponse });
    await choose([new File([JPEG], "p.jpg", { type: "image/jpeg" })]);
    await act(async () => {
      submitButton().click();
    });
    expect(submit).toHaveBeenCalledWith("nb-1", expect.any(File), true);
    expect(getCaptureState().phase).toBe("draft");
    expect(getCaptureState().draft?.fromPicture).toBe(true);
    expect(getCaptureState().draft?.previewImage).toMatch(/^data:image\/webp;base64,/);
    expect(onDraftReady).toHaveBeenCalled();
  });

  it("a server refusal shows its message, keeps the file, and re-enables submit", async () => {
    submit.mockResolvedValue({ ok: false, message: { code: "not_a_recipe", reason: "not_food" } });
    await choose([new File([JPEG], "p.jpg", { type: "image/jpeg" })]);
    await act(async () => {
      submitButton().click();
    });
    expect(container.textContent).toContain("doesn't look like a recipe");
    expect(keptFile()).not.toBeNull();
    expect(submitButton().disabled).toBe(false);
  });

  it("shows the Spanish message under the Spanish locale", async () => {
    prefs.value = { locale: "es" };
    submit.mockResolvedValue({ ok: false, message: { code: "ai_invalid_output" } });
    await choose([new File([JPEG], "p.jpg", { type: "image/jpeg" })]);
    await act(async () => {
      submitButton().click();
    });
    expect(container.textContent).toContain("No pudimos leer esa receta");
  });

  it("pasting an image from the clipboard chooses it", async () => {
    const image = new File([JPEG], "clip.png", { type: "image/png" });
    const event = new Event("paste", { bubbles: true, cancelable: true });
    Object.defineProperty(event, "clipboardData", { value: { files: [image] } });
    await act(async () => {
      document.dispatchEvent(event);
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    expect(keptFile()?.name).toBe("clip.png");
  });

  it("the camera button opens the live camera view when a camera is available", () => {
    Object.defineProperty(navigator, "mediaDevices", {
      value: { getUserMedia: vi.fn(() => new Promise(() => {})) },
      configurable: true,
    });
    act(() => button("Take a photo")!.click());
    expect(container.querySelector("video")).not.toBeNull();
    expect(input().hasAttribute("capture")).toBe(false);
    Object.defineProperty(navigator, "mediaDevices", { value: undefined, configurable: true });
  });

  it("without a camera, the camera button says so instead of opening a file picker", () => {
    Object.defineProperty(navigator, "mediaDevices", { value: undefined, configurable: true });
    act(() => button("Take a photo")!.click());
    expect(container.querySelector("video")).toBeNull();
    expect(container.textContent).toContain("The camera is not available.");
  });
});
