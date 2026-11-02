import { requireAlias } from "@/lib/alias";
import { getServerLocale } from "@/lib/serverLocale";

import { KitchenNotebooksScreen } from "../../KitchenNotebooksScreen";
import styles from "../../kitchens.module.scss";

export const dynamic = "force-dynamic";

/** The kitchen's notebooks as cards, and adding a personal notebook (spec 035 FR-007a). */
export default async function KitchenNotebooksPage({
  params,
}: {
  params: Promise<{ kitchenId: string }>;
}) {
  const { kitchenId } = await params;
  const me = await requireAlias(`/kitchens/${kitchenId}/notebooks`);

  const locale = await getServerLocale();

  return (
    <main className={`${styles.detailMain} flex-1`}>
      <KitchenNotebooksScreen kitchenId={kitchenId} locale={locale} viewerAlias={me.alias} />
    </main>
  );
}
