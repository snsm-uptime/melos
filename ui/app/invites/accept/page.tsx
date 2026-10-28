
import { inviteMessages } from "@/lib/i18n/invite";
import { fetchSession } from "@/lib/session";
import { AcceptInvitePanel } from "./AcceptInvitePanel";
import styles from "../../signup/signup.module.scss";
import { getServerLocale } from "@/lib/serverLocale";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{ token?: string | string[] }>;

export default async function AcceptInvitePage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const params = await searchParams;
  const raw = params.token;
  const token =
    typeof raw === "string" ? raw : Array.isArray(raw) ? (raw[0] ?? "") : "";

  const session = await fetchSession();
  const locale = await getServerLocale();
  const t = inviteMessages[locale];

  return (
    <main className={styles.shell}>
      <div className={styles.card}>
        <h1 className={styles.title}>{t.acceptTitle}</h1>
        <p className={styles.subtitle}>{t.acceptSubtitle}</p>
        <AcceptInvitePanel
          locale={locale}
          token={token}
          authenticated={Boolean(session)}
        />
      </div>
    </main>
  );
}
