import { ClosedLists } from "@/components/ShoppingList";
import { requireAlias } from "@/lib/alias";
import { getServerLocale } from "@/lib/serverLocale";

import styles from "../../kitchens.module.scss";

export const dynamic = "force-dynamic";

/** The kitchen's closed shopping lists (spec 025). */
export default async function KitchenShoppingListsPage({
  params,
}: {
  params: Promise<{ kitchenId: string }>;
}) {
  const { kitchenId } = await params;
  await requireAlias(`/kitchens/${kitchenId}/shopping-lists`);

  const locale = await getServerLocale();

  return (
    <main className={styles.detailMain}>
      <ClosedLists kitchenId={kitchenId} locale={locale} />
    </main>
  );
}
