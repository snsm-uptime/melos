import { requireAlias } from "@/lib/alias";
import { NotebookRecipesScreen } from "./NotebookRecipesScreen";
import { getServerLocale } from "@/lib/serverLocale";

export const dynamic = "force-dynamic";

export default async function NotebookRecipesPage({
  params,
}: {
  params: Promise<{ notebookId: string }>;
}) {
  const { notebookId } = await params;
  await requireAlias(`/notebooks/${notebookId}`);

  const locale = await getServerLocale();

  return <NotebookRecipesScreen notebookId={notebookId} locale={locale} />;
}
