import { redirect } from "next/navigation";

import { ClosingCta, ComingSoon, GroupSection, LandingHero } from "@/components/LandingTour";
import { RedirectIfAuthenticated } from "@/components/RedirectIfAuthenticated";
import { requireAlias } from "@/lib/alias";
import { availableFeatures, groupsInOrder, plannedFeatures } from "@/lib/featureInventory";
import { landingMessages } from "@/lib/i18n/landing";
import { resolveServerAuthenticatedLanding } from "@/lib/serverLanding";
import { getServerLocale } from "@/lib/serverLocale";
import { fetchSession } from "@/lib/session";

export const dynamic = "force-dynamic";

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
      />

      {groupsInOrder().map((group) => (
        <GroupSection
          key={group.id}
          group={group}
          features={availableFeatures(group.id)}
          locale={locale}
          featuresHeading={t.featuresHeading}
        />
      ))}

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
