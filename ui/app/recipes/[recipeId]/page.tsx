import { RecipeDetailScreen } from "@/components/RecipeDetail/RecipeDetailScreen";
import { requireAlias } from "@/lib/alias";
import { getServerLocale } from "@/lib/serverLocale";

export const dynamic = "force-dynamic";

export default async function RecipeDetailPage({
  params,
}: {
  params: Promise<{ recipeId: string }>;
}) {
  const { recipeId } = await params;
  await requireAlias(`/recipes/${recipeId}`);

  const locale = await getServerLocale();

  return <RecipeDetailScreen recipeId={recipeId} locale={locale} />;
}
