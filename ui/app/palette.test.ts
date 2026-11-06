import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

// Reads globals.css, as components/CauldronLoader/contrast.test.ts does, and checks the pairs of
// specs/072-acrylic-nav-palette/contracts/theme-tokens.md (SC-003, FR-013).

const css = readFileSync(join(__dirname, "globals.css"), "utf8");

/** Body of the first block that opens with `selector {` and contains `must`. */
function blockBody(selector: string, must = ""): string {
  let from = 0;
  for (;;) {
    const start = css.indexOf(`${selector} {`, from);
    if (start < 0) throw new Error(`no block ${selector} ${must}`);
    const open = css.indexOf("{", start);
    const close = css.indexOf("}", open);
    const body = css.slice(open + 1, close);
    if (!must || body.includes(must)) return body;
    from = close;
  }
}

function declarations(body: string): Record<string, string> {
  const out: Record<string, string> = {};
  const stripped = body.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const m of stripped.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) out[m[1]] = m[2].trim();
  return out;
}

type RGBA = { r: number; g: number; b: number; a: number };

const NAMED: Record<string, RGBA> = {
  white: { r: 255, g: 255, b: 255, a: 1 },
  black: { r: 0, g: 0, b: 0, a: 1 },
  transparent: { r: 0, g: 0, b: 0, a: 0 },
};

function parseHex(hex: string): RGBA {
  const h = hex.replace("#", "");
  const full = h.length === 3 ? [...h].map((c) => c + c).join("") : h;
  return {
    r: parseInt(full.slice(0, 2), 16),
    g: parseInt(full.slice(2, 4), 16),
    b: parseInt(full.slice(4, 6), 16),
    a: 1,
  };
}

/** Splits "a, b" at top-level commas only. */
function splitTop(s: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let cur = "";
  for (const ch of s) {
    if (ch === "(") depth++;
    if (ch === ")") depth--;
    if (ch === "," && depth === 0) {
      parts.push(cur.trim());
      cur = "";
    } else cur += ch;
  }
  if (cur.trim()) parts.push(cur.trim());
  return parts;
}

/** Resolves var(), color-mix(in srgb, A [p%], B [p%]) (premultiplied, as CSS does), hex and names. */
function resolve(value: string, vars: Record<string, string>): RGBA {
  const v = value.trim();
  const varMatch = /^var\((--[\w-]+)(?:,\s*([^)]+))?\)$/.exec(v);
  if (varMatch) {
    const target = vars[varMatch[1]];
    if (target === undefined) throw new Error(`undefined ${varMatch[1]}`);
    return resolve(target, vars);
  }
  const mix = /^color-mix\(in srgb,\s*(.+)\)$/.exec(v);
  if (mix) {
    const [a, b] = splitTop(mix[1]);
    const parse = (part: string): { c: RGBA; p: number | null } => {
      const m = /^(.*?)\s+(\d+(?:\.\d+)?)%$/.exec(part);
      return m ? { c: resolve(m[1], vars), p: Number(m[2]) / 100 } : { c: resolve(part, vars), p: null };
    };
    const A = parse(a);
    const B = parse(b);
    const pA = A.p ?? (B.p !== null ? 1 - B.p : 0.5);
    const pB = 1 - pA;
    const alpha = pA * A.c.a + pB * B.c.a;
    const ch = (x: number, y: number) => (alpha === 0 ? 0 : (pA * A.c.a * x + pB * B.c.a * y) / alpha);
    return {
      r: ch(A.c.r, B.c.r),
      g: ch(A.c.g, B.c.g),
      b: ch(A.c.b, B.c.b),
      a: alpha,
    };
  }
  if (v.startsWith("#")) return parseHex(v);
  if (NAMED[v]) return NAMED[v];
  throw new Error(`cannot resolve ${value}`);
}

/** The colour as seen on an opaque ground. */
function over(fg: RGBA, ground: RGBA): RGBA {
  return {
    r: fg.r * fg.a + ground.r * (1 - fg.a),
    g: fg.g * fg.a + ground.g * (1 - fg.a),
    b: fg.b * fg.a + ground.b * (1 - fg.a),
    a: 1,
  };
}

function luminance({ r, g, b }: RGBA): number {
  const lin = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function ratio(a: RGBA, b: RGBA): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

const light = declarations(blockBody(":root", "--background:"));
const dark = declarations(blockBody("html.dark"));
const darkPrefers = declarations(blockBody("html:not(.light):not(.dark)"));
const frostAlpha = light["--frost-alpha"];

type Pair = { name: string; ink: string; ground: string; min: number };

/** Ground under the frosted bar or menu: the token mixed at --frost-alpha over the page behind. */
function frosted(vars: Record<string, string>, token: string, base: RGBA): RGBA {
  const layer = resolve(`color-mix(in srgb, var(${token}) ${frostAlpha}, transparent)`, vars);
  return over(layer, base);
}

const TEXT = 4.5;
const UI = 3;

/** The pairs of contracts/theme-tokens.md, by name. Frosted rows are computed over pure black and white. */
const PAIRS: Pair[] = [
  { name: "Text on page", ink: "--foreground", ground: "--background", min: TEXT },
  { name: "Text on surface", ink: "--foreground", ground: "--surface", min: TEXT },
  { name: "Quiet text on page", ink: "--muted", ground: "--background", min: TEXT },
  { name: "Quiet text on surface", ink: "--muted", ground: "--surface", min: TEXT },
  { name: "Main colour text/icon on page", ink: "--accent", ground: "--background", min: TEXT },
  { name: "Main colour text/icon on surface", ink: "--accent", ground: "--surface", min: TEXT },
  { name: "Text on orange fill", ink: "--on-accent", ground: "--accent-fill", min: TEXT },
  { name: "Text on violet fill", ink: "--on-primary", ground: "--primary", min: TEXT },
  { name: "Text on magenta fill", ink: "--on-secondary", ground: "--secondary", min: TEXT },
  { name: "Error text on page", ink: "--error", ground: "--background", min: TEXT },
  { name: "Error text on surface", ink: "--error", ground: "--surface", min: TEXT },
  { name: "Danger text on surface", ink: "--danger", ground: "--surface", min: TEXT },
  { name: "Warning text on page", ink: "--warn", ground: "--background", min: TEXT },
  { name: "Warning text on surface", ink: "--warn", ground: "--surface", min: TEXT },
  { name: "Success text on page", ink: "--owed", ground: "--background", min: TEXT },
  { name: "Success text on surface", ink: "--owed", ground: "--surface", min: TEXT },
  { name: "Input border on surface", ink: "--field-border", ground: "--surface", min: UI },
  { name: "Input border on page", ink: "--field-border", ground: "--background", min: UI },
  { name: "Focus ring on page", ink: "--accent", ground: "--background", min: UI },
  { name: "Focus ring on surface", ink: "--accent", ground: "--surface", min: UI },
  { name: "Text on hovered menu row", ink: "--foreground", ground: "--menu-item-hover", min: TEXT },
  { name: "Text on selected menu row", ink: "--foreground", ground: "--menu-item-selected", min: TEXT },
  { name: "Text on selected card", ink: "--foreground", ground: "--card-selected", min: TEXT },
  { name: "Quiet text on selected card", ink: "--muted", ground: "--card-selected", min: TEXT },
];

const FROSTED: { name: string; ink: string; token: string; min: number }[] = [
  { name: "bar", token: "--background", ink: "--foreground", min: TEXT },
  { name: "bar", token: "--background", ink: "--muted", min: TEXT },
  { name: "bar", token: "--background", ink: "--accent", min: UI },
  { name: "menu", token: "--surface", ink: "--foreground", min: TEXT },
  { name: "menu", token: "--surface", ink: "--muted", min: TEXT },
];

const BASES: { label: string; color: RGBA }[] = [
  { label: "black", color: NAMED.black },
  { label: "white", color: NAMED.white },
];

function checkTheme(vars: Record<string, string>) {
  const failures: string[] = [];
  for (const p of PAIRS) {
    const ground = resolve(vars[p.ground], vars);
    const ink = over(resolve(vars[p.ink], vars), ground);
    const r = ratio(ink, ground);
    if (r < p.min) failures.push(`${p.name}: ${r.toFixed(2)} < ${p.min}`);
  }
  for (const f of FROSTED) {
    for (const base of BASES) {
      const ground = frosted(vars, f.token, base.color);
      const ink = over(resolve(vars[f.ink], vars), ground);
      const r = ratio(ink, ground);
      if (r < f.min) failures.push(`${f.name} ${f.ink} over ${base.label}: ${r.toFixed(2)} < ${f.min}`);
    }
  }
  return failures;
}

/** Merge a theme's roles with the derived rows, which are defined as color-mix in :root. */
function themeVars(base: Record<string, string>): Record<string, string> {
  return { ...light, ...base };
}

describe("palette (spec 072, contracts/theme-tokens.md)", () => {
  it("every light pair meets its minimum, frosted rows included", () => {
    expect(checkTheme(themeVars(light))).toEqual([]);
  });

  it("every dark pair meets its minimum, frosted rows included", () => {
    const vars = { ...themeVars(light), ...dark };
    expect(checkTheme(vars)).toEqual([]);
  });

  it("the two dark blocks declare the same custom properties and values", () => {
    expect(darkPrefers).toEqual(dark);
  });

  it("no warm colour or --wb-* token is left in the palette", () => {
    const oldHexes = ["#f7f3ec", "#fffcf7", "#2a241c", "#6e6456", "#e2d8c8", "#3f6b45", "#a04936", "#2f6e48", "#a6791f", "#8b3a2a", "#4356a3", "#17140f", "#221e17", "#f0e9dc", "#a89b88", "#3a342a", "#8fbb8e", "#d48b78", "#7ec794", "#d9b866", "#adbdff"];
    for (const hex of oldHexes) expect(css).not.toContain(hex);
    expect(css).not.toContain("--wb-");
  });

  it("both themes declare every role of the data model", () => {
    const roles = [
      "--background", "--surface", "--foreground", "--muted", "--border", "--field-border",
      "--accent", "--accent-fill", "--on-accent", "--primary", "--on-primary", "--secondary",
      "--on-secondary", "--error", "--danger", "--danger-strong", "--warn", "--owed",
    ];
    for (const role of roles) {
      expect(light[role], `light ${role}`).toBeDefined();
      expect(dark[role], `dark ${role}`).toBeDefined();
    }
    expect(frostAlpha).toBe("86%");
  });
});
