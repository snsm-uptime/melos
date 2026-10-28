import { kitchensMessages } from "@/lib/i18n/kitchens";
import { getServerLocale } from "@/lib/serverLocale";

import styles from "../kitchens.module.scss";

function Pulse({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-muted ${className}`} />;
}

export default async function KitchenDetailLoading() {
  const t = kitchensMessages[await getServerLocale()];
  return (
    <main
      className={styles.detailMain}
      role="status"
      aria-live="polite"
      aria-label={t.loadingKitchen}
    >
      <div className="flex items-stretch gap-[var(--space-2)]">
        <Pulse className="h-12 min-w-0 flex-1" />
        <Pulse className="h-12 w-32 shrink-0" />
      </div>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(min(100%,18rem),1fr))] gap-[var(--space-2)]">
        {[0, 1, 2, 3].map((i) => (
          <Pulse key={i} className="h-[4.5rem]" />
        ))}
      </div>
    </main>
  );
}
