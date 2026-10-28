import { cookies } from "next/headers";

import { requireAlias } from "@/lib/alias";
import type { Locale } from "@/lib/i18n/locale";
import { NotebookRecipesScreen } from "./NotebookRecipesScreen";

export const dynamic = "force-dynamic";

function resolvePageLocale(languageCookie: string | undefined): Locale {
  if (languageCookie === "es" || languageCookie === "en") return languageCookie;
  return "en";
}

export default async function NotebookRecipesPage({
  params,
}: {
  params: Promise<{ notebookId: string }>;
}) {
  const { notebookId } = await params;
  await requireAlias(`/notebooks/${notebookId}`);

  const jar = await cookies();
  const locale = resolvePageLocale(jar.get("melos_lang_cache")?.value);

  return <NotebookRecipesScreen notebookId={notebookId} locale={locale} />;
}
