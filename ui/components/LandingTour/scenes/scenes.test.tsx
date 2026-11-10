import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { landingMessages, type DemoId } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";

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

/** contracts/landing-page.md, "Scenes": what the still final state shows. */
const FINAL_STATE: Record<DemoId, Record<Locale, string[]>> = {
  overview: {
    en: ["flour — 1 cup + 3 tbsp", "Crepes", "White sauce", "Saved to Ana's Notebook"],
    es: ["harina — 1 taza + 3 cdas", "Crepas", "Salsa blanca", "Guardada en el Cuaderno de Ana"],
  },
  capture: {
    en: ["a pinch of salt", "2 large onions", "Vague amount", "onion", "2 unit large", "Review and save"],
    es: ["una pizca de sal", "2 cebollas grandes", "Cantidad imprecisa", "cebolla", "2 unidad grande", "Revisar y guardar"],
  },
  notebooks: {
    en: ["Ana's Notebook", "Lentil soup", "1 cup", "2 unit", "3 cups"],
    es: ["Cuaderno de Ana", "Sopa de lentejas", "1 taza", "2 unidad", "3 tazas"],
  },
  together: {
    en: ["Our kitchen", "Ana's Notebook", "Leo's Notebook", "Sent to Leo"],
    es: ["Nuestra cocina", "Cuaderno de Ana", "Cuaderno de Leo", "Enviada a Leo"],
  },
  shop: {
    en: ["flour — 1 cup + 3 tbsp", "Crepes", "White sauce", "Market", "eggs — 2", "milk — 2 cups"],
    es: ["harina — 1 taza + 3 cdas", "Crepas", "Salsa blanca", "Mercado", "huevos — 2", "leche — 2 tazas"],
  },
  ingredients: {
    en: ["onion", "cebolla", "“onions” is now another name for “onion”"],
    es: ["cebolla", "onion", "«cebollas» ahora es otro nombre de «cebolla»"],
  },
  home: {
    en: ["Sopa de lentejas", "Lentil soup", "Light", "Dark"],
    es: ["Sopa de lentejas", "Lentil soup", "Claro", "Oscuro"],
  },
};

describe.each(DEMOS)("%s scene", (id) => {
  it.each(["en", "es"] as const)("shows its final state in %s", (locale) => {
    const markup = render(id, locale);
    for (const text of FINAL_STATE[id][locale]) expect(markup, text).toContain(escaped(text));
  });

  it("links nowhere and calls no app route (FR-010)", () => {
    for (const locale of ["en", "es"] as const) {
      const markup = render(id, locale);
      expect(markup).not.toContain("href=");
      expect(markup).not.toContain("/api/");
      expect(markup).not.toMatch(/<(button|a|input|textarea|select)[\s>]/);
    }
  });

  /*
   * FR-013, US4: a scene shows none of the other language's text. Left out on purpose: text that
   * the other language's messages also hold (the ingredient's name in the other language), and the
   * home scene's `card`, which is drawn in both languages to show the switch.
   */
  it("shows no text of the other language (US4)", () => {
    for (const [locale, other] of [
      ["en", "es"],
      ["es", "en"],
    ] as const) {
      const markup = render(id, locale);
      const own = new Set(strings(landingMessages[locale].demo).map((entry) => entry.text));
      const foreign = strings(landingMessages[other].demo[id])
        .filter((entry) => !entry.path.startsWith("card"))
        .filter((entry) => !own.has(entry.text));
      // Whole text nodes only, so Spanish "sal" is not found inside English "salt".
      for (const entry of foreign) {
        expect(markup, `${locale} ${id}.${entry.path}`).not.toContain(`>${escaped(entry.text)}<`);
      }
    }
  });
});
