import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";

import styles from "./NotebookCard.module.scss";

export type NotebookCardProps = {
  name: string;
  ownerAlias: string | null;
  /** Shown only when passed (the Notebook tab). The kitchen section omits it. */
  access?: "owner" | "member" | "kitchen_member";
  isDefault?: boolean;
  /** The signed-in person's alias. The owner line is hidden when the owner is this person. */
  viewerAlias?: string | null;
  locale: Locale;
};

/**
 * Inert notebook card: no link, no button, no click handler (spec 060 FR-014).
 * Tapping a card does nothing until recipes and the notebook page land (S-016, S-021).
 */
export function NotebookCard({
  name,
  ownerAlias,
  access,
  isDefault = false,
  viewerAlias,
  locale,
}: NotebookCardProps) {
  const t = notebooksMessages[locale];
  const ownedByViewer = ownerAlias !== null && ownerAlias === viewerAlias;
  const accessLabel =
    access === "owner"
      ? t.accessOwner
      : access === "member"
        ? t.accessMember
        : access === "kitchen_member"
          ? t.accessKitchenMember
          : null;

  return (
    <article
      className={`${styles.card} relative flex min-w-0 items-stretch gap-[var(--space-3)] rounded-[var(--radius-md)] border border-border bg-surface p-[var(--space-3)]`}
    >
      <span className={styles.spine} aria-hidden="true" />
      <div className="flex min-w-0 flex-1 flex-col gap-[var(--space-1)]">
        <h3 className="m-0 truncate text-[1rem] font-[550] leading-normal text-foreground">
          {name}
        </h3>
        {ownedByViewer ? null : (
          <p className="m-0 text-[0.85rem] text-muted">
            {`${t.ownerLabel} ${ownerAlias ?? t.ownerUnknown}`}
          </p>
        )}
        {accessLabel ? <p className="m-0 text-[0.85rem] text-muted">{accessLabel}</p> : null}
        {isDefault ? (
          <p className="m-0 text-[0.85rem] font-[550] text-accent">{t.defaultMarker}</p>
        ) : null}
      </div>
    </article>
  );
}
