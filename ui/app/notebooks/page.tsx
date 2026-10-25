import { cookies } from "next/headers";

import { requireAlias } from "@/lib/alias";
import type { Locale } from "@/lib/i18n/locale";
import { NotebookTabScreen } from "./NotebookTabScreen";

export const dynamic = "force-dynamic";

function resolvePageLocale(languageCookie: string | undefined): Locale {
  if (languageCookie === "es" || languageCookie === "en") return languageCookie;
  return "en";
}

export default async function NotebookPage() {
  const me = await requireAlias("/notebooks");

  const jar = await cookies();
  const locale = resolvePageLocale(jar.get("melos_lang_cache")?.value);

  return <NotebookTabScreen locale={locale} viewerAlias={me.alias} />;
}
