import styles from "../kitchens.module.scss";

function Pulse({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-muted ${className}`} />;
}

export default function KitchenDetailLoading() {
  return (
    <main
      className={styles.softMain}
      role="status"
      aria-live="polite"
      aria-label="Loading kitchen"
    >
      <div className={styles.softBody}>
        <div className={styles.detailLayout}>
          <div className={styles.detailPrimary}>
            <Pulse className="h-4 w-28" />
            <div className="flex flex-col gap-[var(--space-2)]">
              {[0, 1, 2].map((i) => (
                <div key={i} className="flex items-center gap-[var(--space-2)]">
                  <Pulse className="h-8 w-8 shrink-0 rounded-full" />
                  <Pulse className="h-4 w-32" />
                </div>
              ))}
            </div>
          </div>
          <aside className={styles.detailSidebar}>
            <Pulse className="h-11 w-11" />
          </aside>
        </div>
      </div>
    </main>
  );
}
