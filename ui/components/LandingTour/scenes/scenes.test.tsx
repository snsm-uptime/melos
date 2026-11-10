import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { cartMessages } from "@/lib/i18n/cart";
import { captureMessagesFor } from "@/lib/i18n/capture";
import { catalogMessages } from "@/lib/i18n/catalog";
import { landingMessages, type DemoId } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";
import { messagesFor } from "@/lib/i18n/messages";
import { recipeDetailMessages } from "@/lib/i18n/recipeDetail";
import { recipeShareMessages } from "@/lib/i18n/recipeShare";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";

import { demoFor } from "../demos";

const DEMOS: DemoId[] = ["overview", "capture", "notebooks", "together", "shop", "ingredients", "home"];

function escaped(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");
}

function render(id: DemoId, locale: Locale): string {
  const Scene = demoFor(id);
  return renderToStaticMarkup(<Scene locale={locale} />);
}

/** Every string under a value, with its key path. */
function strings(value: unknown, prefix = ""): { path: string; text: string }[] {
  if (typeof value === "string") return [{ path: prefix, text: value }];
  if (value && typeof value === "object") {
    return Object.entries(value).flatMap(([key, child]) =>
      strings(child, prefix ? `${prefix}.${key}` : key),
    );
  }
  return [];
}

/**
 * contracts/landing-page.md, "Scenes": what the still final state shows. The labels are the app's
 * own messages, which shows the scene is drawn by the app's components; the rest is invented data.
 */
function finalState(id: DemoId, locale: Locale): string[] {
  const d = landingMessages[locale].demo;
  const capture = captureMessagesFor(locale);
  const list = shoppingListMessages[locale];
  const catalog = catalogMessages[locale];
  switch (id) {
    case "overview":
      return [d.overview.recipeA, d.overview.recipeB, d.overview.notebook, d.overview.flour, "1 cup + 3 tbsp"];
    case "capture":
      return [capture.addRecipe, capture.optionUrl, capture.optionPicture, capture.optionText, capture.vague,
        `value="${d.capture.saltAmount}"`, `value="${d.capture.onion}"`, `value="2"`, `value="large" selected`];
    case "notebooks":
      return [d.notebooks.notebook, d.notebooks.recipes[0], recipeDetailMessages[locale].ingredientsTitle,
        `value="2"`, "1 cup", "2 medium", "3 cup"];
    case "together":
      return [d.together.kitchen, d.together.notebookAna, d.together.notebookLeo, d.together.recipe,
        messagesFor(recipeShareMessages, locale).shareSent("Leo")];
    case "shop":
      return [d.shop.recipeA, d.shop.recipeB, cartMessages[locale].serves(4), list.tabCount(d.shop.placeMarket, 1),
        d.shop.flour, "1 cup + 3 tbsp", d.shop.eggs, d.shop.milk];
    case "ingredients":
      return [catalog.merged(d.ingredients.merged, d.ingredients.kept, 1), d.ingredients.kept,
        `${d.ingredients.variant} (${catalog.languageShort[locale === "en" ? "es" : "en"]})`,
        `${d.ingredients.merged} (${catalog.spelling})`];
    case "home":
      return [landingMessages.es.demo.home.card.recipe, landingMessages.en.demo.home.card.recipe, d.home.light, d.home.dark];
  }
}

/** A few of the app's labels the scenes draw; none may show in the other language's page. */
function appLabels(locale: Locale): string[] {
  const capture = captureMessagesFor(locale);
  return [
    capture.addRecipe,
    capture.vague,
    recipeDetailMessages[locale].ingredientsTitle,
    cartMessages[locale].servings,
    shoppingListMessages[locale].allPlaces,
    catalogMessages[locale].keepLabel,
    catalogMessages[locale].confirmMerge,
    messagesFor(recipeShareMessages, locale).shareTitle,
  ];
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe.each(DEMOS)("%s scene", (id) => {
  it.each(["en", "es"] as const)("shows its final state in %s, drawn by the app's components", (locale) => {
    const markup = render(id, locale);
    for (const text of finalState(id, locale)) expect(markup, text).toContain(escaped(text).replace(/&quot;/g, '"'));
  });

  it("links nowhere and calls no app route (FR-010)", () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    for (const locale of ["en", "es"] as const) {
      const markup = render(id, locale);
      expect(markup).not.toContain("href=");
      expect(markup).not.toContain("/api/");
    }
    expect(fetch).not.toHaveBeenCalled();
  });

  /*
   * FR-013, US4: a scene shows none of the other language's text, neither the invented data nor
   * the app's labels. Left out on purpose: text that the other language's messages also hold (the
   * ingredient's name in the other language), and the home scene's `card`, which is drawn in both
   * languages to show the switch.
   */
  it("shows no text of the other language (US4)", () => {
    for (const [locale, other] of [
      ["en", "es"],
      ["es", "en"],
    ] as const) {
      const markup = render(id, locale);
      const own = new Set([
        ...strings(landingMessages[locale].demo).map((entry) => entry.text),
        ...appLabels(locale),
      ]);
      const foreign = [
        ...strings(landingMessages[other].demo[id]).filter((entry) => !entry.path.startsWith("card")),
        ...(id === "home" ? [] : appLabels(other).map((text) => ({ path: "app", text }))),
      ].filter((entry) => !own.has(entry.text));
      // Whole text nodes only, so Spanish "sal" is not found inside English "salt".
      for (const entry of foreign) {
        expect(markup, `${locale} ${id}.${entry.path}`).not.toContain(`>${escaped(entry.text)}<`);
      }
    }
  });
});
