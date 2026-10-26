import { requireAlias } from "@/lib/alias";
import { RecipeDraftPage } from "@/components/RecipeDraft/RecipeDraftPage";

export const dynamic = "force-dynamic";

export default async function NotebookDraftPage() {
  await requireAlias("/notebooks/draft");
  return <RecipeDraftPage />;
}
