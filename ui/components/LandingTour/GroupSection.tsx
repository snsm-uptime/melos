import type { ReactNode } from "react";

import type { Feature, FeatureGroup } from "@/lib/featureInventory";
import type { Locale } from "@/lib/i18n/locale";

export type GroupSectionProps = {
  group: FeatureGroup;
  /** The group's available features, in inventory order (FR-004, FR-005). */
  features: readonly Feature[];
  locale: Locale;
  featuresHeading: string;
  demo?: ReactNode;
};

/**
 * One feature group of the tour: title, lede, the group's feature list and its demo. One column on
 * phones; from md the text and the demo sit side by side, swapping sides from one group to the next.
 */
export function GroupSection({ group, features, locale, featuresHeading, demo }: GroupSectionProps) {
  const demoFirst = group.order % 2 === 0;
  return (
    <section
      id={group.id}
      data-landing-section
      aria-labelledby={`${group.id}-title`}
      className="mx-auto grid max-w-5xl grid-cols-1 items-center gap-8 px-page-gutter py-12 md:grid-cols-2 md:gap-12"
    >
      <div className="flex min-w-0 flex-col gap-3">
        <h2 id={`${group.id}-title`} className="m-0 text-[1.5rem] font-semibold leading-[1.2]">
          {group.title[locale]}
        </h2>
        <p className="m-0 text-muted leading-[1.5]">{group.lede[locale]}</p>
        <h3 className="m-0 mt-2 text-[0.75rem] font-semibold uppercase tracking-[0.05em] text-muted">
          {featuresHeading}
        </h3>
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {features.map((feature) => (
            <li key={feature.id} className="flex flex-col leading-[1.4]">
              <strong className="font-semibold">{feature.name[locale]}</strong>
              <span className="text-[0.9rem] text-muted">{feature.summary[locale]}</span>
            </li>
          ))}
        </ul>
      </div>
      {demo ? <div className={`min-w-0 ${demoFirst ? "md:order-first" : ""}`}>{demo}</div> : null}
    </section>
  );
}
