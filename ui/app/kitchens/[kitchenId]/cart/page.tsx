import { CartScreen } from "@/components/Cart";
import { requireAlias } from "@/lib/alias";
import { getServerLocale } from "@/lib/serverLocale";

import styles from "../../kitchens.module.scss";

export const dynamic = "force-dynamic";

/** The kitchen's shared cart (spec 022, contracts/cart-ui.md). */
export default async function KitchenCartPage({
  params,
}: {
  params: Promise<{ kitchenId: string }>;
}) {
  const { kitchenId } = await params;
  await requireAlias(`/kitchens/${kitchenId}/cart`);

  const locale = await getServerLocale();

  return (
    <main className={styles.detailMain}>
      <CartScreen kitchenId={kitchenId} locale={locale} />
    </main>
  );
}
