// Reused from finance-dashboard/ui/app/sign-in/page.tsx
import { redirect } from "next/navigation";

import { RedirectIfAuthenticated } from "@/components/RedirectIfAuthenticated";
import { SignedOutLanguageSwitch } from "@/components/SignedOutLanguageSwitch";
import { signInMessages } from "@/lib/i18n/signin";
import { resolveServerAuthenticatedLanding } from "@/lib/serverLanding";
import { fetchSession } from "@/lib/session";
import { safeReturnTo } from "./signInClient";
import { SignInChrome } from "./SignInChrome";
import { SignInForm } from "./SignInForm";
import styles from "../signup/signup.module.scss";
import { getServerLocale } from "@/lib/serverLocale";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{ returnTo?: string | string[] }>;

export default async function SignInPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const params = await searchParams;
  const rawReturnTo = Array.isArray(params.returnTo)
    ? params.returnTo[0]
    : params.returnTo;
  const hasExplicitReturn =
    typeof rawReturnTo === "string" && rawReturnTo.trim().length > 0;
  const landing = hasExplicitReturn
    ? safeReturnTo(rawReturnTo)
    : await resolveServerAuthenticatedLanding();

  const session = await fetchSession();
  if (session) {
    redirect(landing);
  }

  const locale = await getServerLocale();
  const t = signInMessages[locale];

  return (
    <main className={styles.shell}>
      <RedirectIfAuthenticated to={hasExplicitReturn ? landing : "/"} />
      <SignInChrome />
      <div className={styles.card}>
        <h1 className={styles.title}>{t.title}</h1>
        <p className={styles.subtitle}>{t.subtitle}</p>
        <SignInForm locale={locale} returnTo={rawReturnTo} />
        {/* In the card's column, right below the sign-up link. */}
        <div className={styles.languageRow}>
          <SignedOutLanguageSwitch placement="inline" />
        </div>
      </div>
    </main>
  );
}
