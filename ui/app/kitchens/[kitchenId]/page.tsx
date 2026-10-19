import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { Avatar } from "@/components/Avatar";
import { SectionLabel } from "@/components/soft-ledger/SectionLabel";
import { requireAlias } from "@/lib/alias";
import { getApiInternalUrl } from "@/lib/api";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import type { Locale } from "@/lib/i18n/locale";
import { fetchSession } from "@/lib/session";
import { KitchenDetailChrome } from "../KitchenDetailChrome";
import { KitchenDetailMobileActions } from "../KitchenDetailMobileActions";
import { TemporalNavigation } from "../TemporalNavigation";
import { memberLabel, type KitchenMember } from "../kitchensClient";
import styles from "../kitchens.module.scss";

export const dynamic = "force-dynamic";

type DetailPayload = {
  id?: string;
  name?: string;
  owner_id?: string;
};

function resolvePageLocale(languageCookie: string | undefined): Locale {
  if (languageCookie === "es" || languageCookie === "en") return languageCookie;
  return "en";
}

async function cookieHeader(): Promise<string> {
  const jar = await cookies();
  return jar
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
}

/** Defensive parse — malformed/absent rows are skipped, never fabricated. */
export function asMembers(data: unknown): KitchenMember[] {
  if (!data || typeof data !== "object") return [];
  const rows = (data as { members?: unknown }).members;
  if (!Array.isArray(rows)) return [];
  const out: KitchenMember[] = [];
  for (const row of rows) {
    if (!row || typeof row !== "object") continue;
    const m = row as { user_id?: unknown; alias?: unknown; photo_base64?: unknown };
    if (typeof m.user_id !== "string") continue;
    out.push({
      user_id: m.user_id,
      alias: typeof m.alias === "string" && m.alias ? m.alias : null,
      photo_base64: typeof m.photo_base64 === "string" ? m.photo_base64 : null,
    });
  }
  return out;
}

export default async function KitchenDetailPage({
  params,
}: {
  params: Promise<{ kitchenId: string }>;
}) {
  const { kitchenId } = await params;
  const session = await fetchSession();
  if (!session) {
    redirect(`/sign-in?returnTo=/kitchens/${encodeURIComponent(kitchenId)}`);
  }
  await requireAlias(`/kitchens/${kitchenId}`);

  const jar = await cookies();
  const locale = resolvePageLocale(jar.get("fh_lang_cache")?.value);
  const t = kitchensMessages[locale];
  const header = await cookieHeader();
  const requestInit: RequestInit = {
    method: "GET",
    headers: {
      Accept: "application/json",
      ...(header ? { Cookie: header } : {}),
    },
    cache: "no-store",
  };

  let detail: DetailPayload | null = null;
  let members: KitchenMember[] = [];
  let membersLoadError = false;
  let notFound = false;
  let loadError = false;
  try {
    const response = await fetch(
      `${getApiInternalUrl()}/kitchens/${encodeURIComponent(kitchenId)}`,
      requestInit,
    );
    if (response.status === 401) {
      redirect(`/sign-in?returnTo=/kitchens/${encodeURIComponent(kitchenId)}`);
    }
    if (response.status === 404) {
      notFound = true;
    } else if (response.ok) {
      const [detailData, membersRes] = await Promise.all([
        response.json() as Promise<DetailPayload>,
        fetch(`${getApiInternalUrl()}/kitchens/${encodeURIComponent(kitchenId)}/members`, requestInit),
      ]);
      detail = detailData;
      if (membersRes.ok) {
        members = asMembers(await membersRes.json());
        membersLoadError = members.length === 0;
      } else {
        membersLoadError = true;
      }
    } else {
      loadError = true;
    }
  } catch {
    loadError = true;
  }

  const kitchenTitle = detail?.name;
  const isOwner = Boolean(detail?.owner_id && detail.owner_id === session.user_id);
  const showKitchenDetail = Boolean(kitchenTitle) && !notFound && !loadError;

  const inviteMessages = {
    inviteTitle: t.inviteTitle,
    inviteLabel: t.inviteLabel,
    inviteSubmit: t.inviteSubmit,
    inviteSending: t.inviteSending,
    inviteSent: t.inviteSent,
    errorGeneric: t.errorGeneric,
    errorInvalidName: t.errorInvalidName,
    errorInvalidEmail: t.errorInvalidEmail,
    errorForbidden: t.errorInviteForbidden,
    errorUnauthorized: t.errorUnauthorized,
    errorAlreadyMember: t.errorAlreadyMember,
    errorSmtp: t.errorSmtp,
  };

  return (
    <main className={styles.softMain}>
      <div className={styles.softBody}>
        {notFound || !showKitchenDetail ? (
          <>
            <KitchenDetailChrome title={notFound ? t.detailNotFound : t.loadError} />
            <p className={`${styles.copy} ${styles.softBack}`}>
              <Link className={styles.link} href="/home">
                {t.backToKitchens}
              </Link>
            </p>
          </>
        ) : (
          <div className={styles.detailLayout}>
            <KitchenDetailChrome title={kitchenTitle as string} />
            <div className={styles.detailPrimary}>
              <div className="flex items-center justify-between gap-[var(--space-2)]">
                <SectionLabel>{t.detailMembersTitle}</SectionLabel>
                <KitchenDetailMobileActions
                  kitchenId={kitchenId}
                  canInvite={isOwner}
                  inviteMessages={inviteMessages}
                  inviteAria={t.mobileInviteAria}
                  closeLabel={t.mobileSheetClose}
                />
              </div>
              {membersLoadError ? (
                <p className={styles.copy} role="alert">
                  {t.loadError}
                </p>
              ) : (
                <ul className="m-0 flex list-none flex-col gap-[var(--space-2)] p-0">
                  {members.map((member) => (
                    <li key={member.user_id} className="flex items-center gap-[var(--space-2)]">
                      <Avatar
                        alias={member.alias}
                        seed={member.user_id}
                        photoBase64={member.photo_base64 ?? null}
                      />
                      <span>{memberLabel(member)}</span>
                      {member.user_id === detail?.owner_id ? (
                        <span className="text-muted text-[0.85rem]">{t.ownerBadge}</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <aside className={styles.detailSidebar}>
              <TemporalNavigation kitchenId={kitchenId} isOwner={isOwner} inviteMessages={inviteMessages} />
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}
