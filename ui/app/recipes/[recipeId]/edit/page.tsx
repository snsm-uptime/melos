import { RecipeEditScreen } from "@/components/RecipeEdit/RecipeEditScreen";
import { requireAlias } from "@/lib/alias";
import { getServerLocale } from "@/lib/serverLocale";

export const dynamic = "force-dynamic";

export default async function RecipeEditPage({
  params,
}: {
  params: Promise<{ recipeId: string }>;
}) {
  const { recipeId } = await params;
  await requireAlias(`/recipes/${recipeId}/edit`);

  const locale = await getServerLocale();

  return <RecipeEditScreen recipeId={recipeId} locale={locale} />;
}
