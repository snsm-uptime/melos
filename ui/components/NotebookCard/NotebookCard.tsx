import Link from "next/link";

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
  /** When given, the card links to the notebook's recipe list (spec 021 FR-013). */
  href?: string;
};

/**
 * Notebook card. With `href` it is a link to the notebook's recipe list (spec 021 FR-013);
 * without it the card is inert: no link, no button, no click handler (spec 060 FR-014).
 */
export function NotebookCard({
  name,
  ownerAlias,
  access,
  isDefault = false,
  viewerAlias,
  locale,
  href,
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

  const card = (
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

  if (!href) return card;
  return (
    <Link
      href={href}
      className="block rounded-[var(--radius-md)] text-inherit no-underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      {card}
    </Link>
  );
}
