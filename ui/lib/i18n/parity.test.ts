import { describe, expect, it } from "vitest";

import { accountMessages } from "./account";
import { aliasMessages } from "./alias";
import { captureText } from "./capture";
import { cartMessages } from "./cart";
import { inviteMessages } from "./invite";
import { kitchensMessages } from "./kitchens";
import { landingMessages } from "./landing";
import { notebooksMessages } from "./notebooks";
import { passwordResetMessages } from "./password-reset";
import { recipeDetailMessages } from "./recipeDetail";
import { recipeListMessages } from "./recipeLists";
import { shoppingListMessages } from "./shoppingList";
import { sidePanelMessages } from "./sidePanel";
import { signInMessages } from "./signin";
import { signupMessages } from "./signup";
import { verifyMessages } from "./verify";

/**
 * Spec 063 FR-009 / SC-002: every interface message exists in both languages. A message that
 * exists in one language only fails the build here, so it is caught before release.
 */
const SETS: Record<string, { en: unknown; es: unknown }> = {
  account: accountMessages,
  alias: aliasMessages,
  capture: captureText,
  cart: cartMessages,
  invite: inviteMessages,
  kitchens: kitchensMessages,
  landing: landingMessages,
  notebooks: notebooksMessages,
  passwordReset: passwordResetMessages,
  recipeDetail: recipeDetailMessages,
  recipeLists: recipeListMessages,
  shoppingList: shoppingListMessages,
  sidePanel: sidePanelMessages,
  signIn: signInMessages,
  signup: signupMessages,
  verify: verifyMessages,
};

/**
 * Text that is the same in both languages on purpose: a language named in its own language, a
 * product or file-format word, an example, a symbol. One reason per entry (reviewed once).
 */
const SAME_ON_PURPOSE = new Set<string>([
  "account.en", // the language "English", written in English in both languages
  "account.es", // the language "Español", written in Spanish in both languages
  "account.photoCropZoom", // "Zoom" is the word used in Spanish too
  "alias.photoCropZoom", // "Zoom", as above
  "alias.label", // "Alias" is the same word in Spanish
  "capture.optionUrl", // "URL"
]);

function paths(value: unknown, prefix = ""): { path: string; leaf: unknown }[] {
  if (value && typeof value === "object") {
    return Object.entries(value).flatMap(([key, child]) =>
      paths(child, prefix ? `${prefix}.${key}` : key),
    );
  }
  return [{ path: prefix, leaf: value }];
}

describe.each(Object.entries(SETS))("%s messages", (name, set) => {
  const en = paths(set.en);
  const es = paths(set.es);
  const esByPath = new Map(es.map((entry) => [entry.path, entry.leaf]));

  it("has the same keys in English and Spanish (a message exists in one language only)", () => {
    expect(es.map((e) => e.path).sort(), `${name}: spec 063 FR-009`).toEqual(
      en.map((e) => e.path).sort(),
    );
  });

  it("has no empty Spanish message and the same kind of value in both", () => {
    for (const { path, leaf } of en) {
      const other = esByPath.get(path);
      expect(typeof other, `${name}.${path}`).toBe(typeof leaf);
      if (typeof other === "string") expect(other.trim().length, `${name}.${path}`).toBeGreaterThan(0);
      if (typeof leaf === "function") {
        expect((other as () => void).length, `${name}.${path} arity`).toBe((leaf as () => void).length);
      }
    }
  });

  it("does not leave an English text as the Spanish one by mistake", () => {
    const same = en
      .filter(({ path, leaf }) => typeof leaf === "string" && esByPath.get(path) === leaf)
      .map(({ path }) => `${name}.${path}`)
      .filter((full) => !SAME_ON_PURPOSE.has(full));
    expect(same, "untranslated, or add it to SAME_ON_PURPOSE with a reason").toEqual([]);
  });
});
