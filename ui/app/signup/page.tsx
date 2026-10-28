import { redirect } from "next/navigation";

import { RedirectIfAuthenticated } from "@/components/RedirectIfAuthenticated";
import { signupMessages } from "@/lib/i18n/signup";
import { resolveServerAuthenticatedLanding } from "@/lib/serverLanding";
import { fetchSession } from "@/lib/session";
import { SignupForm } from "./SignupForm";
import styles from "./signup.module.scss";
import { getServerLocale } from "@/lib/serverLocale";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{ invite?: string | string[] }>;

export default async function SignupPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const params = await searchParams;
  const rawInvite = params.invite;
  const inviteToken =
    typeof rawInvite === "string"
      ? rawInvite
      : Array.isArray(rawInvite)
        ? (rawInvite[0] ?? "")
        : "";

  const session = await fetchSession();
  if (session) {
    if (inviteToken) {
      redirect(`/invites/accept?token=${encodeURIComponent(inviteToken)}`);
    }
    redirect(await resolveServerAuthenticatedLanding());
  }

  const locale = await getServerLocale();
  const t = signupMessages[locale];

  return (
    <main className={styles.shell}>
      <RedirectIfAuthenticated
        to={
          inviteToken
            ? `/invites/accept?token=${encodeURIComponent(inviteToken)}`
            : "/"
        }
      />
      <div className={styles.card}>
        <h1 className={styles.title}>{t.title}</h1>
        {!inviteToken ? <p className={styles.subtitle}>{t.subtitle}</p> : null}
        <SignupForm locale={locale} inviteToken={inviteToken || undefined} />
      </div>
    </main>
  );
}
