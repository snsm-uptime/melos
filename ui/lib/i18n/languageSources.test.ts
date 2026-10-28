import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * Guard (spec 063 FR-010): the interface language comes from one place on the server
 * (`getServerLocale()`) and from the preferences provider in the browser. These guesses were
 * removed and must not come back.
 */
const ROOT = join(__dirname, "..", "..");
const FORBIDDEN: { name: string; pattern: RegExp }[] = [
  { name: "detectLocale", pattern: /detectLocale/ },
  { name: "browserLocale", pattern: /browserLocale/ },
  { name: "Accept-Language header", pattern: /accept-language/i },
  { name: "the old language cache key", pattern: /melos_lang_cache/ },
  { name: 'a hard-coded <html lang="en">', pattern: /<html[^>]*\blang="en"/ },
];

function sources(dir: string, found: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      if (entry === "node_modules" || entry === ".next") continue;
      sources(path, found);
    } else if (/\.(ts|tsx)$/.test(entry) && !/\.test\.(ts|tsx)$/.test(entry)) {
      found.push(path);
    }
  }
  return found;
}

describe("language sources", () => {
  // The BFF routes in app/api only pass request headers on to the api; they decide nothing.
  const files = ["app", "components", "lib"]
    .flatMap((dir) => sources(join(ROOT, dir)))
    .filter((file) => !relative(ROOT, file).startsWith(join("app", "api")));

  it.each(FORBIDDEN)("no source guesses the language from $name", ({ pattern, name }) => {
    const offenders = files
      .filter((file) => pattern.test(readFileSync(file, "utf8")))
      .map((file) => relative(ROOT, file));
    expect(
      offenders,
      `${name} found: the language comes from getServerLocale() on the server and the provider on the client (spec 063 FR-010)`,
    ).toEqual([]);
  });
});
