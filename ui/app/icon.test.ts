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

/**
 * The logo's colours, frozen: spec 072 FR-016 keeps the logo unchanged while the app palette moves
 * to the portfolio's. These are the Warm Balance values the logo was drawn in.
 */
const LOGO = {
  light: { bg: "#f7f3ec", text: "#2a241c", ink: "#4356a3" },
  dark: { bg: "#17140f", text: "#f0e9dc", ink: "#adbdff" },
};

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
    const rules = (text: string, ink: string, background: string) =>
      `.pot{fill:${mixed(text, background, MARK_POT_STRENGTH)}}` +
      `.ink{fill:${mixed(ink, background, MARK_INK_STRENGTH)}}`;

    expect(svg).toContain(`<style>${rules(LOGO.light.text, LOGO.light.ink, LOGO.light.bg)}@media`);
    expect(svg).toContain(
      `(prefers-color-scheme:dark){${rules(LOGO.dark.text, LOGO.dark.ink, LOGO.dark.bg)}}</style>`,
    );
  });
});
