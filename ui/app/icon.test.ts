import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import {
  BUBBLES,
  CAULDRON_SHAPES,
  MARK_INK_STRENGTH,
  MARK_POT_STRENGTH,
  MARK_VIEWBOX_ATTR,
} from "@/components/CauldronLoader/geometry";

const globals = readFileSync(resolve(__dirname, "globals.css"), "utf8");

/** A token's value in each theme, in file order: light, then dark. */
function themed(token: string): string[] {
  return [...globals.matchAll(new RegExp(`${token}: (#[0-9a-f]{6});`, "g"))].map((m) => m[1]);
}

/** What the logo's color-mix gives, for an icon that can't read the theme. */
function mixed(colour: string, background: string, percent: number): string {
  const channels = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const [from, to] = [channels(colour), channels(background)];
  const strength = percent / 100;
  return `#${from
    .map((channel, i) => Math.round(channel * strength + to[i] * (1 - strength)))
    .map((channel) => channel.toString(16).padStart(2, "0"))
    .join("")}`;
}

describe("browser icon", () => {
  const svg = readFileSync(resolve(__dirname, "icon.svg"), "utf8");

  it("is the loader's cauldron: every shape of its drawing", () => {
    for (const { d } of Object.values(CAULDRON_SHAPES)) {
      expect(svg).toContain(`d="${d}"`);
    }
    for (const { cx, cy, r } of BUBBLES) {
      expect(svg).toContain(`cx="${cx}" cy="${cy}" r="${r}"`);
    }
  });

  it("uses the same square crop as the logo", () => {
    expect(svg).toContain(`viewBox="${MARK_VIEWBOX_ATTR}"`);
  });

  it("has the logo's colours in the light and dark themes", () => {
    const [lightBg, darkBg] = themed("--wb-bg");
    const [lightText, darkText] = themed("--wb-text");
    const [lightInk, darkInk] = themed("--secondary");
    const rules = (text: string, ink: string, background: string) =>
      `.pot{fill:${mixed(text, background, MARK_POT_STRENGTH)}}` +
      `.ink{fill:${mixed(ink, background, MARK_INK_STRENGTH)}}`;

    expect(svg).toContain(`<style>${rules(lightText, lightInk, lightBg)}@media`);
    expect(svg).toContain(
      `(prefers-color-scheme:dark){${rules(darkText, darkInk, darkBg)}}</style>`,
    );
  });
});
