import { notebookInviteMessages } from "@/lib/i18n/invite";
import { fetchSession } from "@/lib/session";
import { getServerLocale } from "@/lib/serverLocale";
import { AcceptNotebookInvitePanel } from "./AcceptNotebookInvitePanel";
import styles from "../../signup/signup.module.scss";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{ token?: string | string[] }>;

export default async function NotebookInvitePage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const params = await searchParams;
  const raw = params.token;
  const token = typeof raw === "string" ? raw : Array.isArray(raw) ? (raw[0] ?? "") : "";

  const session = await fetchSession();
  const locale = await getServerLocale();
  const t = notebookInviteMessages[locale];

  return (
    <main className={styles.shell}>
      <div className={styles.card}>
        <h1 className={styles.title}>{t.title}</h1>
        <AcceptNotebookInvitePanel
          locale={locale}
          token={token}
          authenticated={Boolean(session)}
        />
      </div>
    </main>
  );
}
