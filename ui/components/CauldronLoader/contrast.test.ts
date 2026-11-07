import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * Spec 065 SC-003: every colour the loader draws reaches a contrast of 3:1 against what is behind
 * it, in both themes. The tokens are read from globals.css so this stays in step with the theme.
 */

type Rgb = readonly [number, number, number];

const css = readFileSync(resolve(__dirname, "../../app/globals.css"), "utf8");

function declarations(selector: RegExp): Record<string, string> {
  const match = selector.exec(css);
  if (!match) throw new Error(`no ${selector} block in globals.css`);
  const body = match[1].replace(/\/\*[\s\S]*?\*\//g, "");
  return Object.fromEntries(
    [...body.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]),
  );
}

const THEMES = {
  light: declarations(/^:root\s*\{([^}]*)\}/m),
  dark: declarations(/^html\.dark\s*\{([^}]*)\}/m),
} as const;

/** Splits on commas that are not inside brackets. */
function splitTop(text: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let start = 0;
  for (let i = 0; i < text.length; i += 1) {
    if (text[i] === "(") depth += 1;
    else if (text[i] === ")") depth -= 1;
    else if (text[i] === "," && depth === 0) {
      parts.push(text.slice(start, i).trim());
      start = i + 1;
    }
  }
  parts.push(text.slice(start).trim());
  return parts;
}

/** A colour operand of color-mix: `<colour>` or `<colour> <percent>%`. */
function operand(text: string, vars: Record<string, string>): { rgb: Rgb; percent?: number } {
  const match = /^(.*?)(?:\s+([\d.]+)%)?$/.exec(text.trim()) as RegExpExecArray;
  return {
    rgb: parse(match[1], vars),
    percent: match[2] === undefined ? undefined : Number(match[2]),
  };
}

function parse(expr: string, vars: Record<string, string>): Rgb {
  const text = expr.trim();
  const variable = /^var\((--[\w-]+)\)$/.exec(text);
  if (variable) {
    const value = vars[variable[1]];
    if (value === undefined) throw new Error(`unknown token ${variable[1]}`);
    return parse(value, vars);
  }
  if (text === "white") return [255, 255, 255];
  if (text === "black") return [0, 0, 0];
  const hex = /^#([0-9a-f]{6})$/i.exec(text);
  if (hex) {
    const n = parseInt(hex[1], 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  const mix = /^color-mix\(in srgb,([\s\S]*)\)$/.exec(text);
  if (mix) {
    const [first, second] = splitTop(mix[1]).map((part) => operand(part, vars));
    const p1 = first.percent ?? (second.percent === undefined ? 50 : 100 - second.percent);
    const w = p1 / 100;
    return first.rgb.map((c, i) => c * w + second.rgb[i] * (1 - w)) as unknown as Rgb;
  }
  throw new Error(`cannot read colour: ${text}`);
}

function luminance([r, g, b]: Rgb): number {
  const [lr, lg, lb] = [r, g, b].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
}

function contrast(a: Rgb, b: Rgb): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

/** The tokens of one theme, with the colours the loader and the buttons use. */
function colours(theme: keyof typeof THEMES) {
  const vars = THEMES[theme];
  const c = (expr: string) => parse(expr, vars);
  return { c };
}

/** Button fills and text, as set per variant in BaseButton.module.scss (data-model.md). */
const VARIANTS = {
  primary: { ink: "var(--on-primary)", fill: "var(--primary)" },
  accent: { ink: "var(--on-secondary)", fill: "var(--secondary)" },
  ghost: {
    ink: "var(--accent)",
    fill: "color-mix(in srgb, var(--accent) 8%, var(--surface))",
  },
  headerIcon: { ink: "var(--accent)", fill: "var(--background)" },
} as const;

const bubbleOf = (ink: string, fill: string) => `color-mix(in srgb, ${ink} 80%, ${fill})`;

describe.each(Object.keys(THEMES) as (keyof typeof THEMES)[])("loader contrast, %s theme", (theme) => {
  const { c } = colours(theme);

  it("shows the accent bubbles and drip against the background and the surface", () => {
    expect(contrast(c("var(--accent-fill)"), c("var(--background)"))).toBeGreaterThanOrEqual(3);
    expect(contrast(c("var(--accent-fill)"), c("var(--surface)"))).toBeGreaterThanOrEqual(3);
  });

  it("shows the page cauldron against the background and the surface", () => {
    expect(contrast(c("var(--cauldron-body)"), c("var(--background)"))).toBeGreaterThanOrEqual(3);
    expect(contrast(c("var(--cauldron-body)"), c("var(--surface)"))).toBeGreaterThanOrEqual(3);
  });

  it.each(Object.entries(VARIANTS))(
    "shows the cauldron, bubbles and drip on a %s button",
    (_name, { ink, fill }) => {
      expect(contrast(c(ink), c(fill))).toBeGreaterThanOrEqual(3);
      expect(contrast(c(bubbleOf(ink, fill)), c(fill))).toBeGreaterThanOrEqual(3);
    },
  );
});
