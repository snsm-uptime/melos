import type { Feature } from "@/lib/featureInventory";
import type { Locale } from "@/lib/i18n/locale";

export type ComingSoonProps = {
  features: readonly Feature[];
  locale: Locale;
  title: string;
  lede: string;
};

/** Planned features (FR-004): names and one sentence each, no demos, no dates; absent when none. */
export function ComingSoon({ features, locale, title, lede }: ComingSoonProps) {
  if (features.length === 0) return null;
  return (
    <section
      id="coming-soon"
      data-landing-section
      aria-labelledby="coming-soon-title"
      className="mx-auto flex max-w-5xl flex-col gap-4 px-page-gutter py-12"
    >
      <div className="flex flex-col gap-1">
        <h2 id="coming-soon-title" className="m-0 text-[1.25rem] font-semibold leading-[1.2]">
          {title}
        </h2>
        <p className="m-0 text-muted leading-[1.5]">{lede}</p>
      </div>
      <ul className="m-0 grid list-none grid-cols-1 gap-3 p-0 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((feature) => (
          <li
            key={feature.id}
            className="flex flex-col gap-1 rounded-[var(--radius-md)] border border-dashed border-border p-4 leading-[1.4]"
          >
            <strong className="font-semibold">{feature.name[locale]}</strong>
            <span className="text-[0.9rem] text-muted">{feature.summary[locale]}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
