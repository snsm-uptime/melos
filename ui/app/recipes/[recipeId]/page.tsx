import { cookies } from "next/headers";

import { RecipeDetailScreen } from "@/components/RecipeDetail/RecipeDetailScreen";
import { requireAlias } from "@/lib/alias";
import type { Locale } from "@/lib/i18n/locale";

export const dynamic = "force-dynamic";

function resolvePageLocale(languageCookie: string | undefined): Locale {
  if (languageCookie === "es" || languageCookie === "en") return languageCookie;
  return "en";
}

export default async function RecipeDetailPage({
  params,
}: {
  params: Promise<{ recipeId: string }>;
}) {
  const { recipeId } = await params;
  await requireAlias(`/recipes/${recipeId}`);

  const jar = await cookies();
  const locale = resolvePageLocale(jar.get("melos_lang_cache")?.value);

  return <RecipeDetailScreen recipeId={recipeId} locale={locale} />;
}
