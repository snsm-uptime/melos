/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DraftView } from "@/lib/capture/captureStore";
import { ToastProvider, useToastState } from "@/components/Toast/ToastProvider";

import { usePictureDisclaimer } from "./usePictureDisclaimer";

const prefs = vi.hoisted(() => ({
  value: null as null | { ready: boolean; locale: "en" | "es"; me: { disclaimers: boolean } | null },
}));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));

const draft = (overrides: Partial<DraftView> = {}): DraftView => ({
  title: "Soup",
  baseServings: 4,
  servingsEstimated: false,
  lines: [],
  steps: [],
  catalog: [],
  fromPicture: true,
  ...overrides,
});

function Probe({ value, saveKey }: { value: DraftView | null; saveKey: string | null }) {
  usePictureDisclaimer(value, saveKey);
  const state = useToastState();
  return <p>{state?.toasts.map((toast) => `${toast.id}|${toast.durationMs}|${toast.text}`).join(";")}</p>;
}

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  vi.useFakeTimers();
  prefs.value = { ready: true, locale: "en", me: { disclaimers: true } };
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.useRealTimers();
});

function render(value: DraftView | null, saveKey: string | null = "key-1") {
  act(() => root.render(<ToastProvider><Probe value={value} saveKey={saveKey} /></ToastProvider>));
}

const text = () => container.querySelector("p")?.textContent ?? "";

describe("usePictureDisclaimer", () => {
  it("shows one toast for a picture draft, for 10 seconds", () => {
    render(draft());
    expect(text()).toContain("picture-disclaimer|10000|");
    expect(text()).toContain("This draft was read from a picture");
  });

  it("shows nothing when the account turned the disclaimers off", () => {
    prefs.value = { ready: true, locale: "en", me: { disclaimers: false } };
    render(draft());
    expect(text()).toBe("");
  });

  it("shows nothing while preferences are not ready, then shows once they are", () => {
    prefs.value = { ready: false, locale: "en", me: null };
    render(draft());
    expect(text()).toBe("");
    prefs.value = { ready: true, locale: "en", me: { disclaimers: true } };
    render(draft());
    expect(text()).toContain("picture-disclaimer");
  });

  it("never shows for a text, link or manual draft", () => {
    render(draft({ fromPicture: false }));
    expect(text()).toBe("");
    render(draft({ fromPicture: undefined }));
    expect(text()).toBe("");
  });

  it("editing the draft does not show it again", () => {
    render(draft());
    act(() => vi.advanceTimersByTime(11_000));
    expect(text()).toBe("");
    render(draft({ title: "Soup, edited" }));
    expect(text()).toBe("");
  });

  it("leaving the page dismisses it", () => {
    render(draft());
    act(() => root.unmount());
    root = createRoot(container);
    render(null);
    expect(text()).toBe("");
  });

  it("is Spanish under the Spanish locale", () => {
    prefs.value = { ready: true, locale: "es", me: { disclaimers: true } };
    render(draft());
    expect(text()).toContain("Este borrador se leyó de una imagen");
  });
});
