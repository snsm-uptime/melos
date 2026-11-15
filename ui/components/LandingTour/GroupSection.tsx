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
  /**
   * "split": the text and the demo side by side from md, swapping sides from one group to the
   * next. "stacked": the title and lede, then the demo, then the features in a row, one column
   * per feature from md.
   */
  layout?: "split" | "stacked";
};

/** One feature group of the tour: title, lede, the group's feature list and its demo. One column on phones. */
export function GroupSection({
  group,
  features,
  locale,
  featuresHeading,
  demo,
  layout = "split",
}: GroupSectionProps) {
  const header = (
    <>
      <h2 id={`${group.id}-title`} className="m-0 text-[1.5rem] font-semibold leading-[1.2]">
        {group.title[locale]}
      </h2>
      <p className="m-0 text-muted leading-[1.5]">{group.lede[locale]}</p>
    </>
  );
  const featureHeading = (
    <h3 className="m-0 mt-2 text-[0.75rem] font-semibold uppercase tracking-[0.05em] text-muted">
      {featuresHeading}
    </h3>
  );
  const featureItems = features.map((feature) => (
    <li key={feature.id} className="flex flex-col leading-[1.4]">
      <strong className="font-semibold">{feature.name[locale]}</strong>
      <span className="text-[0.9rem] text-muted">{feature.summary[locale]}</span>
    </li>
  ));

  if (layout === "stacked") {
    return (
      <section
        id={group.id}
        data-landing-section
        aria-labelledby={`${group.id}-title`}
        className="mx-auto flex max-w-5xl flex-col gap-6 px-page-gutter py-12"
      >
        <div className="flex max-w-2xl flex-col gap-3">{header}</div>
        {demo ? <div className="min-w-0">{demo}</div> : null}
        <div className="flex flex-col gap-3">
          {featureHeading}
          <ul className="m-0 grid list-none grid-cols-1 gap-x-8 gap-y-4 p-0 sm:grid-cols-2 md:auto-cols-fr md:grid-flow-col md:grid-cols-none">
            {featureItems}
          </ul>
        </div>
      </section>
    );
  }

  const demoFirst = group.order % 2 === 0;
  return (
    <section
      id={group.id}
      data-landing-section
      aria-labelledby={`${group.id}-title`}
      className="mx-auto grid max-w-5xl grid-cols-1 items-center gap-8 px-page-gutter py-12 md:grid-cols-2 md:gap-12"
    >
      <div className="flex min-w-0 flex-col gap-3">
        {header}
        {featureHeading}
        <ul className="m-0 flex list-none flex-col gap-2 p-0">{featureItems}</ul>
      </div>
      {demo ? <div className={`min-w-0 ${demoFirst ? "md:order-first" : ""}`}>{demo}</div> : null}
    </section>
  );
}
