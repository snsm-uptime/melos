import type { ReactNode } from "react";

import styles from "./Tabs.module.scss";

/** The app's tab switch: a `tablist` of underlined tabs, each with an icon and a label. */
export function TabList({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div role="tablist" aria-label={label} className={styles.tabs}>
      {children}
    </div>
  );
}

export function TabButton({
  id,
  selected,
  onSelect,
  icon,
  label,
}: {
  id: string;
  selected: boolean;
  onSelect: () => void;
  icon: ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      role="tab"
      id={id}
      aria-selected={selected}
      className={selected ? `${styles.tab} ${styles.tabActive}` : styles.tab}
      onClick={onSelect}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
