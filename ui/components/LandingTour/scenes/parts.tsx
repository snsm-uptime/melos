import type { ReactNode } from "react";

import { InlineDialogs } from "@/components/ActionDialog";

import styles from "./scenes.module.scss";

/** A point of the scene's loop (scenes.module.scss `$slots`). */
export type Slot = 1 | 2 | 3 | 4 | 5 | 6;

/** Fades in at the slot; shown in the final state. */
export const inAt = (slot: Slot) => styles[`in${slot}`] ?? "";
/** Fades out at the slot; gone in the final state. */
export const outAt = (slot: Slot) => styles[`out${slot}`] ?? "";
/** A short bump at the slot. */
export const popAt = (slot: Slot) => styles[`pop${slot}`] ?? "";

/** The handler given to the app's controls: the scene is inert, so nothing ever calls it. */
export function ignore(): void {}

/**
 * The root of every scene: the loop length, and the app's dialogs drawn in place (InlineDialogs)
 * rather than as modals over the page.
 */
export function Scene({ long = false, children }: { long?: boolean; children: ReactNode }) {
  return (
    <InlineDialogs>
      <div className={`${styles.scene} ${long ? styles.long : ""}`}>{children}</div>
    </InlineDialogs>
  );
}

/**
 * Two states of the app in one place: `before` until the slot, then `after` (the final state).
 * Both share one grid cell, so the frame keeps the taller one's height and nothing shifts.
 */
export function Swap({ before, after, slot }: { before: ReactNode; after: ReactNode; slot: Slot }) {
  return (
    <div className={styles.swap}>
      <div className={`min-w-0 ${outAt(slot)}`}>{before}</div>
      <div className={`min-w-0 ${inAt(slot)}`}>{after}</div>
    </div>
  );
}

/** A list for the app's row components (they render `<li>`); one per row that moves on its own. */
export function Rows({ className = "", children }: { className?: string; children: ReactNode }) {
  return <ul className={`m-0 flex list-none flex-col gap-2 p-0 ${className}`}>{children}</ul>;
}
