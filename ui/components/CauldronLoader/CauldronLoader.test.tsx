/** @vitest-environment jsdom */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mount } from "@/components/Cart/testRoot";
import { PrimaryButton } from "@/components/soft-ledger/PrimaryButton";

const prefs = vi.hoisted(() => ({ value: null as { locale: "en" | "es" } | null }));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));

import { CauldronLoader } from "./CauldronLoader";
import { CAULDRON_TILT_DEFAULT, CAULDRON_TILT_IN_BUTTON } from "./tilt";

describe("CauldronLoader markup", () => {
  let view: ReturnType<typeof mount>;

  beforeEach(() => {
    view = mount();
  });
  afterEach(() => view.unmount());

  const root = () => view.container.querySelector("span") as HTMLElement;
  const svg = () => view.container.querySelector("svg") as SVGSVGElement;
  const parts = (name: string) => view.container.querySelectorAll(`[data-part="${name}"]`);

  it("is a live status in page tone", () => {
    view.render(<CauldronLoader />);
    expect(root().getAttribute("role")).toBe("status");
    expect(root().getAttribute("aria-live")).toBe("polite");
  });

  it("has no role or live region in button tone, and still holds the hidden text", () => {
    view.render(<CauldronLoader tone="button" />);
    expect(root().hasAttribute("role")).toBe(false);
    expect(root().hasAttribute("aria-live")).toBe(false);
    expect(root().querySelector(".sr-only")?.textContent).toBe("Loading");
  });

  it("sets the width in page tone and the height in button tone, never both", () => {
    view.render(<CauldronLoader />);
    expect(root().style.width).toBe("50%");
    expect(root().style.maxWidth).toBe("10rem");
    expect(root().style.height).toBe("");

    view.render(<CauldronLoader tone="button" />);
    expect(root().style.height).toBe("1.2em");
    expect(root().style.width).toBe("");
  });

  it("takes a size in the dimension of its tone", () => {
    view.render(<CauldronLoader size="2rem" />);
    expect(root().style.width).toBe("2rem");
    expect(root().style.maxWidth).toBe("");

    view.render(<CauldronLoader tone="button" size="1.25rem" />);
    expect(root().style.height).toBe("1.25rem");
  });

  it("hides the drawing from assistive technology", () => {
    view.render(<CauldronLoader />);
    expect(svg().getAttribute("aria-hidden")).toBe("true");
    expect(svg().getAttribute("focusable")).toBe("false");
    expect(svg().querySelector("title")).toBeNull();
  });

  it("draws a body, a rim, two handles, two feet and a drip", () => {
    view.render(<CauldronLoader />);
    const cauldron = svg().querySelector("g:last-of-type") as SVGGElement;
    expect(cauldron.querySelectorAll("path").length).toBe(7);
    expect(parts("body").length).toBe(1);
    expect(parts("rim").length).toBe(1);
    expect(parts("handle").length).toBe(2);
    expect(parts("foot").length).toBe(2);
    expect(parts("drip").length).toBe(1);
  });

  it("draws bubbles of different sizes outside the cauldron group", () => {
    view.render(<CauldronLoader />);
    const circles = Array.from(svg().querySelectorAll("circle"));
    expect(circles.length).toBeGreaterThanOrEqual(2);
    expect(new Set(circles.map((circle) => circle.getAttribute("r"))).size).toBeGreaterThanOrEqual(2);
    const cauldron = svg().querySelector("g:last-of-type") as SVGGElement;
    expect(cauldron.querySelector("circle")).toBeNull();
  });

  it("uses no id, clip path, mask or gradient", () => {
    view.render(<CauldronLoader />);
    expect(view.container.innerHTML).not.toMatch(/\sid=/);
    expect(view.container.querySelector("clipPath, mask, linearGradient, radialGradient")).toBeNull();
  });

  it("keeps two loaders on one screen independent", () => {
    view.render(
      <>
        <CauldronLoader tilt={30} />
        <CauldronLoader tone="button" />
      </>,
    );
    const roots = Array.from(
      view.container.querySelectorAll<HTMLElement>("span[style*='--cauldron-tilt']"),
    );
    expect(roots.length).toBe(2);
    expect(roots[0]).not.toBe(roots[1]);
    expect(roots[0].style.getPropertyValue("--cauldron-tilt")).toBe("30deg");
    expect(roots[1].style.getPropertyValue("--cauldron-tilt")).toBe(`${CAULDRON_TILT_IN_BUTTON}deg`);
    expect(view.container.querySelectorAll("[id]").length).toBe(0);
  });
});

describe("CauldronLoader tilt", () => {
  let view: ReturnType<typeof mount>;

  beforeEach(() => {
    view = mount();
  });
  afterEach(() => view.unmount());

  const tiltOf = (node: ReactNode) => {
    view.render(node);
    return (view.container.querySelector("span") as HTMLElement).style.getPropertyValue(
      "--cauldron-tilt",
    );
  };

  it("rocks to the default angle", () => {
    expect(tiltOf(<CauldronLoader />)).toBe(`${CAULDRON_TILT_DEFAULT}deg`);
  });

  it("rocks to the button default angle in a button", () => {
    expect(tiltOf(<CauldronLoader tone="button" />)).toBe(`${CAULDRON_TILT_IN_BUTTON}deg`);
  });

  it("rocks to the angle it is given", () => {
    expect(tiltOf(<CauldronLoader tilt={10} />)).toBe("10deg");
  });

  it("stays upright at 0", () => {
    expect(tiltOf(<CauldronLoader tilt={0} />)).toBe("0deg");
  });

  it("ignores the sign of a negative angle", () => {
    expect(tiltOf(<CauldronLoader tilt={-10} />)).toBe("10deg");
  });

  it("limits the angle to 45", () => {
    expect(tiltOf(<CauldronLoader tilt={90} />)).toBe("45deg");
  });

  it("takes the tone default for a value that is not a number", () => {
    expect(tiltOf(<CauldronLoader tilt={Number.NaN} />)).toBe(`${CAULDRON_TILT_DEFAULT}deg`);
    expect(tiltOf(<CauldronLoader tilt={"x" as unknown as number} />)).toBe(
      `${CAULDRON_TILT_DEFAULT}deg`,
    );
    expect(tiltOf(<CauldronLoader tone="button" tilt={Number.NaN} />)).toBe(
      `${CAULDRON_TILT_IN_BUTTON}deg`,
    );
  });
});

describe("CauldronLoader placement", () => {
  let view: ReturnType<typeof mount>;

  beforeEach(() => {
    view = mount();
  });
  afterEach(() => view.unmount());

  it("centres a page loader in a stage around it, and puts className on the stage", () => {
    view.render(<CauldronLoader className="py-8" />);
    const stage = view.container.firstElementChild as HTMLElement;
    expect(stage.tagName).toBe("DIV");
    expect(stage.className).toContain("stage");
    expect(stage.className).toContain("py-8");
    expect(stage.querySelector("[role='status']")).not.toBeNull();
  });

  it("adds no stage in a button, and puts className on the loader itself", () => {
    view.render(<CauldronLoader tone="button" className="ml-1" />);
    const root = view.container.firstElementChild as HTMLElement;
    expect(root.tagName).toBe("SPAN");
    expect(root.className).toContain("ml-1");
    expect(view.container.querySelector("div")).toBeNull();
  });
});

describe("CauldronLoader label", () => {
  let view: ReturnType<typeof mount>;

  beforeEach(() => {
    prefs.value = null;
    view = mount();
  });
  afterEach(() => {
    prefs.value = null;
    view.unmount();
  });

  const hiddenText = () => view.container.querySelector(".sr-only")?.textContent;

  it("says Loading with no provider", () => {
    view.render(<CauldronLoader />);
    expect(hiddenText()).toBe("Loading");
  });

  it("says Cargando in Spanish", () => {
    prefs.value = { locale: "es" };
    view.render(<CauldronLoader />);
    expect(hiddenText()).toBe("Cargando");
  });

  it("replaces the text with a label", () => {
    prefs.value = { locale: "es" };
    view.render(<CauldronLoader label="Loading your kitchen" />);
    expect(hiddenText()).toBe("Loading your kitchen");
  });

  it("puts the text in a button's accessible name", () => {
    view.render(<PrimaryButton loading>Save</PrimaryButton>);
    const button = view.container.querySelector("button") as HTMLButtonElement;
    expect(button.hasAttribute("aria-label")).toBe(false);
    expect(button.textContent).toMatch(/Loading/);
    expect(button.getAttribute("aria-busy")).toBe("true");
  });

  it("puts the Spanish text in a button's accessible name", () => {
    prefs.value = { locale: "es" };
    view.render(<PrimaryButton loading>Guardar</PrimaryButton>);
    expect(view.container.querySelector("button")?.textContent).toMatch(/Cargando/);
  });

  it("does not describe the drawing", () => {
    view.render(<CauldronLoader />);
    const svg = view.container.querySelector("svg") as SVGSVGElement;
    expect(svg.getAttribute("aria-hidden")).toBe("true");
    expect(svg.querySelector("title, desc")).toBeNull();
    expect(svg.hasAttribute("aria-label")).toBe(false);
  });
});

describe("CauldronLoader stylesheet", () => {
  const scss = readFileSync(resolve(__dirname, "CauldronLoader.module.scss"), "utf8");
  const stripped = scss.replace(/\/\*[\s\S]*?\*\//g, "");

  /** The text between the braces of the first `@media (...)` block that opens with `query`. */
  function mediaBlock(query: string): string {
    const start = stripped.indexOf(query);
    expect(start).toBeGreaterThanOrEqual(0);
    let depth = 0;
    for (let i = stripped.indexOf("{", start); i < stripped.length; i += 1) {
      if (stripped[i] === "{") depth += 1;
      if (stripped[i] === "}") {
        depth -= 1;
        if (depth === 0) return stripped.slice(stripped.indexOf("{", start) + 1, i);
      }
    }
    throw new Error("unclosed @media block");
  }

  it("moves things only inside prefers-reduced-motion: no-preference", () => {
    const motion = mediaBlock("@media (prefers-reduced-motion: no-preference)");
    const outside = stripped.replace(motion, "");

    expect(outside).not.toMatch(/animation/);
    expect(outside).not.toMatch(/@keyframes/);
    expect(outside).not.toMatch(/transition/);
    expect(motion).toMatch(/@keyframes cauldron-bubble-rise/);
    expect(motion).toMatch(/@keyframes cauldron-rock/);
    expect(motion.match(/animation:/g)?.length).toBeGreaterThanOrEqual(2);
  });

  it("animates only transform and opacity", () => {
    const motion = mediaBlock("@media (prefers-reduced-motion: no-preference)");
    const properties = [...motion.matchAll(/^\s*([a-z-]+)\s*:/gm)].map((m) => m[1]);
    const allowed = new Set([
      "transform",
      "opacity",
      "animation",
      "animation-delay",
      "animation-timing-function",
    ]);
    expect(properties.filter((name) => !allowed.has(name))).toEqual([]);
  });

  it("leaves the bubbles visible in the still pose", () => {
    const outside = stripped.replace(
      mediaBlock("@media (prefers-reduced-motion: no-preference)"),
      "",
    );
    expect(outside).not.toMatch(/opacity\s*:\s*0\b/);
    expect(outside).not.toMatch(/display\s*:\s*none/);
    expect(outside).not.toMatch(/visibility\s*:\s*hidden/);
    expect(outside).toMatch(/\.bubble/);
  });
});
