import { ClosedListDetail } from "@/components/ShoppingList";
import { requireAlias } from "@/lib/alias";
import { getServerLocale } from "@/lib/serverLocale";

import styles from "../../../kitchens.module.scss";

export const dynamic = "force-dynamic";

/** One closed shopping list, read only (spec 025). */
export default async function KitchenShoppingListPage({
  params,
}: {
  params: Promise<{ kitchenId: string; listId: string }>;
}) {
  const { kitchenId, listId } = await params;
  await requireAlias(`/kitchens/${kitchenId}/shopping-lists/${listId}`);

  const locale = await getServerLocale();

  return (
    <main className={styles.detailMain}>
      <ClosedListDetail kitchenId={kitchenId} listId={listId} locale={locale} />
    </main>
  );
}
