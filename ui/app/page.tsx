import { redirect } from "next/navigation";

import {
  ClosingCta,
  ComingSoon,
  Glows,
  GroupSection,
  LandingHero,
  TourDemo,
  TourIndex,
} from "@/components/LandingTour";
import { RedirectIfAuthenticated } from "@/components/RedirectIfAuthenticated";
import { requireAlias } from "@/lib/alias";
import {
  availableFeatures,
  groupsInOrder,
  plannedFeatures,
  type FeatureGroup,
  type GroupId,
} from "@/lib/featureInventory";
import { landingMessages } from "@/lib/i18n/landing";
import { resolveServerAuthenticatedLanding } from "@/lib/serverLanding";
import { getServerLocale } from "@/lib/serverLocale";
import { fetchSession } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Groups with the title above the demo and their features in columns below it; the rest are split. */
const STACKED: ReadonlySet<GroupId> = new Set<GroupId>(["notebooks", "ingredients"]);

/** Groups drawn together on a full-width surface band, to give the page some depth. */
const BANDED: ReadonlySet<GroupId> = new Set<GroupId>(["together", "shop"]);

/** The groups in order, cut into runs of banded and plain groups. */
function runs(groups: readonly FeatureGroup[]): { banded: boolean; groups: FeatureGroup[] }[] {
  const out: { banded: boolean; groups: FeatureGroup[] }[] = [];
  for (const group of groups) {
    const banded = BANDED.has(group.id);
    const last = out.at(-1);
    if (last && last.banded === banded) last.groups.push(group);
    else out.push({ banded, groups: [group] });
  }
  return out;
}

export default async function Home() {
  const session = await fetchSession();
  if (session) {
    const destination = await resolveServerAuthenticatedLanding();
    // First signed-in visit (verify-off) must claim an alias before kitchen chrome.
    await requireAlias(destination);
    redirect(destination);
  }

  const locale = await getServerLocale();
  const t = landingMessages[locale];

  // The feature tour (spec 075): every list on the page comes from lib/featureInventory.ts.
  return (
    <main>
      <RedirectIfAuthenticated />

      <LandingHero
        headline={t.headline}
        intro={t.intro}
        createAccount={t.createAccount}
        signIn={t.signIn}
        demo={<TourDemo id="overview" locale={locale} />}
      />

      <TourIndex groups={groupsInOrder()} locale={locale} label={t.indexLabel} />

      {runs(groupsInOrder()).map((run) => {
        const sections = run.groups.map((group) => (
          <GroupSection
            key={group.id}
            group={group}
            features={availableFeatures(group.id)}
            locale={locale}
            featuresHeading={t.featuresHeading}
            demo={<TourDemo id={group.id} locale={locale} />}
            layout={STACKED.has(group.id) ? "stacked" : "split"}
          />
        ));
        return run.banded ? (
          <div
            key={run.groups[0].id}
            data-landing-band
            className="relative isolate overflow-hidden border-y border-border bg-surface"
          >
            <Glows place="band" />
            {sections}
          </div>
        ) : (
          sections
        );
      })}

      <ComingSoon
        features={plannedFeatures()}
        locale={locale}
        title={t.comingSoonTitle}
        lede={t.comingSoonLede}
      />

      <ClosingCta
        title={t.closingTitle}
        body={t.closingBody}
        createAccount={t.createAccount}
        signIn={t.signIn}
      />
    </main>
  );
}
