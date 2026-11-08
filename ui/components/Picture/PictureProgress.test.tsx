/** @vitest-environment jsdom */

import { captureText } from "@/lib/i18n/capture";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PictureProgress, pickPhrase, PICTURE_STEPS, progressAt } from "./PictureProgress";

const prefs = vi.hoisted(() => ({ value: null as { locale: "en" | "es" } | null }));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  vi.useFakeTimers();
  prefs.value = null;
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.useRealTimers();
});

function render(handwritten: boolean) {
  act(() => root.render(<PictureProgress handwritten={handwritten} />));
}

function barValue(): number {
  return Number(container.querySelector('[role="progressbar"]')?.getAttribute("aria-valuenow"));
}

describe("progressAt", () => {
  it("moves through the steps in order", () => {
    const order = [0, 1_500, 2_500, 4_000, 7_000, 18_000].map((ms) => progressAt(ms).step);
    expect(order).toEqual(["upload", "prepare", "identify", "compress", "read", "draft"]);
  });

  it("never reaches the end before the answer does", () => {
    const total = PICTURE_STEPS.reduce((sum, step) => sum + step.ms, 0);
    expect(progressAt(total * 10).fraction).toBeLessThan(1);
  });
});

describe("the phrase", () => {
  const phrases = captureText.en.progressPhrases;

  it("is one of the six while the picture is printed", () => {
    expect(phrases).toHaveLength(6);
    expect(phrases).toContain(pickPhrase(phrases, "x", false, () => 0.99));
  });

  it("is the handwriting phrase only when Handwritten is on", () => {
    expect(pickPhrase(phrases, captureText.en.progressHandwrittenPhrase, true)).toBe(
      "Understanding your calligraphy",
    );
  });

  it("has a Spanish version of every phrase", () => {
    expect(captureText.es.progressPhrases).toHaveLength(phrases.length);
    expect(captureText.es.progressHandwrittenPhrase).not.toBe(
      captureText.en.progressHandwrittenPhrase,
    );
  });
});

describe("PictureProgress", () => {
  it("shows the handwriting phrase for a handwritten picture", () => {
    render(true);
    expect(container.textContent).toContain("Understanding your calligraphy");
  });

  it("advances the bar as time passes", () => {
    render(false);
    const start = barValue();
    act(() => vi.advanceTimersByTime(8_000));
    expect(barValue()).toBeGreaterThan(start);
  });

  it("shows Spanish under the Spanish locale", () => {
    prefs.value = { locale: "es" };
    render(true);
    expect(container.textContent).toContain("Entendiendo tu letra");
  });
});
