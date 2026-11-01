import { CauldronLoader } from "@/components/CauldronLoader";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { getServerLocale } from "@/lib/serverLocale";

import styles from "../kitchens.module.scss";

export default async function KitchenDetailLoading() {
  const t = kitchensMessages[await getServerLocale()];
  return (
    <main className={`${styles.detailMain} flex-1`}>
      <CauldronLoader label={t.loadingKitchen} />
    </main>
  );
}
