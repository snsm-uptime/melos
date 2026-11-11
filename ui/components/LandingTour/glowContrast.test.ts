import { readFileSync } from "node:fs";
import { resolve as resolvePath } from "node:path";

import { describe, expect, it } from "vitest";

// SC-007 (spec 075): over the strongest point of each landing glow, foreground and muted text keep
// 4.5:1 in both themes. Reads globals.css, as app/palette.test.ts does; the glow is the colour at
// its peak strength composited over the place's background (Glows.tsx draws it as a radial
// gradient whose centre stop has exactly that strength).

const css = readFileSync(resolvePath(__dirname, "../../app/globals.css"), "utf8");

const THEMES = {
  light: ":root, .theme-light-scope",
  dark: "html.dark, .theme-dark-scope",
} as const;

/** Body of the first block that opens with `selector {`. */
function blockBody(selector: string): string {
  const start = css.indexOf(`${selector} {`);
  if (start < 0) throw new Error(`no block ${selector}`);
  const open = css.indexOf("{", start);
  return css.slice(open + 1, css.indexOf("}", open));
}

function declarations(body: string): Record<string, string> {
  const out: Record<string, string> = {};
  const stripped = body.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const m of stripped.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) out[m[1]] = m[2].trim();
  return out;
}

type RGB = { r: number; g: number; b: number };

/** A token's colour: a hex value, or var() of another token. */
function colour(name: string, vars: Record<string, string>): RGB {
  const value = vars[name];
  if (value === undefined) throw new Error(`undefined ${name}`);
  const ref = /^var\((--[\w-]+)\)$/.exec(value);
  if (ref) return colour(ref[1], vars);
  const hex = /^#([0-9a-f]{6})$/i.exec(value);
  if (!hex) throw new Error(`${name} is not a hex colour: ${value}`);
  return {
    r: parseInt(hex[1].slice(0, 2), 16),
    g: parseInt(hex[1].slice(2, 4), 16),
    b: parseInt(hex[1].slice(4, 6), 16),
  };
}

function over(top: RGB, alpha: number, bottom: RGB): RGB {
  const mix = (a: number, b: number) => alpha * a + (1 - alpha) * b;
  return { r: mix(top.r, bottom.r), g: mix(top.g, bottom.g), b: mix(top.b, bottom.b) };
}

function luminance({ r, g, b }: RGB): number {
  const lin = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function contrast(a: RGB, b: RGB): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

/** Where the glows are, and the background each sits on (FR-018). */
const PLACES = { band: "--surface", closing: "--background" } as const;
const GLOWS = [
  { colour: "--accent-fill", strength: "--glow-accent-strength" },
  { colour: "--primary", strength: "--glow-primary-strength" },
] as const;

describe.each(Object.entries(THEMES))("landing glows, %s theme", (_theme, selector) => {
  const vars = declarations(blockBody(selector));

  it.each(GLOWS)("$strength is a visible glow, never a solid wash", ({ strength }) => {
    const value = Number(vars[strength]);
    expect(value, strength).toBeGreaterThanOrEqual(0.05);
    expect(value, strength).toBeLessThanOrEqual(0.5);
  });

  for (const [place, background] of Object.entries(PLACES)) {
    it.each(GLOWS)(`keeps text at 4.5:1 over the $colour glow on the ${place} (SC-007)`, (glow) => {
      const peak = over(colour(glow.colour, vars), Number(vars[glow.strength]), colour(background, vars));
      for (const text of ["--foreground", "--muted"]) {
        expect(contrast(colour(text, vars), peak), `${text} on ${place}`).toBeGreaterThanOrEqual(4.5);
      }
    });
  }
});
