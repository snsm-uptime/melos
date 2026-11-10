import type { FeatureGroup } from "@/lib/featureInventory";
import type { Locale } from "@/lib/i18n/locale";

export type TourIndexProps = {
  groups: readonly FeatureGroup[];
  locale: Locale;
  label: string;
};

/**
 * The tour's index (US3): one link per group to its section. Plain fragment links, so they work
 * without JavaScript and the address can be shared (`/#shop`). The row wraps on narrow phones.
 */
export function TourIndex({ groups, locale, label }: TourIndexProps) {
  return (
    <nav aria-label={label} className="mx-auto max-w-5xl px-page-gutter pb-4">
      <ul className="m-0 flex list-none flex-wrap justify-center gap-2 p-0">
        {groups.map((group) => (
          <li key={group.id}>
            <a
              href={`#${group.id}`}
              className="inline-flex items-center rounded-[var(--radius-md)] border border-border bg-surface px-3 py-1.5 text-[0.85rem] font-[550] no-underline transition-colors hover:border-accent hover:text-accent focus-visible:border-accent focus-visible:text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              {group.title[locale]}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
