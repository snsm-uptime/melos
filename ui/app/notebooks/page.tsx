import { requireAlias } from "@/lib/alias";
import { NotebookTabScreen } from "./NotebookTabScreen";
import { getServerLocale } from "@/lib/serverLocale";

export const dynamic = "force-dynamic";

export default async function NotebookPage() {
  const me = await requireAlias("/notebooks");

  const locale = await getServerLocale();

  return (
    <NotebookTabScreen locale={locale} viewerAlias={me.alias} />
  );
}
