import type { ReactNode } from "react";

import styles from "./scenes.module.scss";

/** A point of the scene's loop (scenes.module.scss `$slots`). */
export type Slot = 1 | 2 | 3 | 4 | 5 | 6;

/** Fades in at the slot; shown in the final state. */
export const inAt = (slot: Slot) => styles[`in${slot}`] ?? "";
/** Fades out at the slot; gone in the final state. */
export const outAt = (slot: Slot) => styles[`out${slot}`] ?? "";
/** A short bump at the slot. */
export const popAt = (slot: Slot) => styles[`pop${slot}`] ?? "";

/** The root of every scene: the loop length and the scene's type size. */
export function Scene({ long = false, children }: { long?: boolean; children: ReactNode }) {
  return <div className={`${styles.scene} ${long ? styles.long : ""}`}>{children}</div>;
}

/** A small surface in the app's card look, with an optional header. */
export function MiniCard({
  title,
  icon,
  className = "",
  children,
}: {
  title?: ReactNode;
  icon?: ReactNode;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <div
      className={`flex min-w-0 flex-col gap-2 rounded-[var(--radius-md)] border border-border bg-surface p-3 text-foreground shadow-elevation-1 ${className}`}
    >
      {title ? (
        <div className="flex min-w-0 items-center gap-1.5 font-semibold">
          {icon ? <span className="flex shrink-0 text-accent [&_svg]:size-4">{icon}</span> : null}
          <span className="min-w-0 truncate">{title}</span>
        </div>
      ) : null}
      {children}
    </div>
  );
}

/** Two states in one place: `before` until the slot, then `after` (the final state). */
export function Swap({ before, after, slot }: { before: ReactNode; after: ReactNode; slot: Slot }) {
  return (
    <span className={styles.swap}>
      <span className={outAt(slot)}>{before}</span>
      <span className={inAt(slot)}>{after}</span>
    </span>
  );
}

/** A line through the text, drawn at the slot (an item marked bought). */
export function Struck({ slot, children }: { slot: Slot; children: ReactNode }) {
  return (
    <span className="relative inline-block text-muted">
      {children}
      <span className={`${styles.strikeLine} ${styles[`strike${slot}`] ?? ""}`} />
    </span>
  );
}

/** A non-interactive button look (scenes hold no controls: they are hidden from assistive tech). */
export function FakeButton({ className = "", children }: { className?: string; children: ReactNode }) {
  return (
    <span
      className={`inline-flex w-fit items-center gap-1.5 rounded-[var(--radius-sm)] bg-primary px-3 py-1 text-[0.75rem] font-semibold text-on-primary ${className}`}
    >
      {children}
    </span>
  );
}

/** A line of the shopping list: name and amounts, then one chip per recipe. */
export function ListLine({ children, chips }: { children: ReactNode; chips?: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
      <span className="min-w-0">{children}</span>
      {chips ? <span className="flex flex-wrap gap-1">{chips}</span> : null}
    </div>
  );
}
