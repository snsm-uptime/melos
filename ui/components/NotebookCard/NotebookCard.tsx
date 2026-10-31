import Link from "next/link";

import { BookmarkIcon } from "@/app/icons";
import { Chip } from "@/components/Chip";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";

import styles from "./NotebookCard.module.scss";

export type NotebookCardProps = {
  name: string;
  ownerAlias: string | null;
  recipeCount: number;
  /** Shown only when passed (the Notebook tab). The kitchen section omits it. */
  access?: "owner" | "member" | "kitchen_member";
  isDefault?: boolean;
  /** The signed-in person's alias. The owner chip is hidden when the owner is this person. */
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
  recipeCount,
  access,
  isDefault = false,
  viewerAlias,
  locale,
  href,
}: NotebookCardProps) {
  const t = notebooksMessages[locale];
  const showOwner = ownerAlias === null || ownerAlias !== viewerAlias;
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
        <h3 className="m-0 break-words text-[1rem] font-[550] leading-normal text-foreground">
          {name}
        </h3>
        <p className="m-0 text-[0.85rem] text-muted">{t.recipeCount(recipeCount)}</p>
        {showOwner || accessLabel ? (
          <div className="mt-[var(--space-1)] flex flex-wrap gap-[var(--space-1)]">
            {showOwner ? (
              <Chip tone="accent">
                <span className="sr-only">{`${t.ownerLabel} `}</span>
                {ownerAlias ?? t.ownerUnknown}
              </Chip>
            ) : null}
            {accessLabel ? (
              <Chip tone={access === "owner" ? "accent" : "muted"}>{accessLabel}</Chip>
            ) : null}
          </div>
        ) : null}
      </div>
      {isDefault ? (
        <span role="img" aria-label={t.defaultMarker} className="flex-shrink-0 self-start text-accent">
          <BookmarkIcon className="block size-5" />
        </span>
      ) : null}
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
