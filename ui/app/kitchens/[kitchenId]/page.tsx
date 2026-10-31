import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { requireAlias } from "@/lib/alias";
import { getApiInternalUrl } from "@/lib/api";
import { cartMessages } from "@/lib/i18n/cart";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { fetchSession } from "@/lib/session";
import { KitchenCartCountProvider } from "../cartCount";
import {
  KitchenDetailChrome,
  type KitchenManage,
  type KitchenShare,
} from "../KitchenDetailChrome";
import { KitchenNotebooksSection } from "../KitchenNotebooksSection";
import type { KitchenMember } from "../kitchensClient";
import styles from "../kitchens.module.scss";
import { getServerLocale } from "@/lib/serverLocale";

export const dynamic = "force-dynamic";

type DetailPayload = {
  id?: string;
  name?: string;
  owner_id?: string;
  is_archived?: boolean;
};

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

  const locale = await getServerLocale();
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
  let defaultKitchenId: string | null = null;
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
      const [detailData, membersRes, panelRes] = await Promise.all([
        response.json() as Promise<DetailPayload>,
        fetch(`${getApiInternalUrl()}/kitchens/${encodeURIComponent(kitchenId)}/members`, requestInit),
        fetch(`${getApiInternalUrl()}/side-panel`, requestInit),
      ]);
      detail = detailData;
      if (panelRes.ok) {
        const panel = (await panelRes.json()) as { default_kitchen_id?: string | null };
        defaultKitchenId = panel.default_kitchen_id ?? null;
      }
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

  const share: KitchenShare | undefined = isOwner
    ? {
        kitchenId,
        ownerId: detail?.owner_id,
        members,
        membersLoadError,
        inviteMessages,
        labels: {
          open: t.mobileInviteAria,
          close: t.mobileSheetClose,
          membersTitle: t.detailMembersTitle,
          ownerBadge: t.ownerBadge,
          loadError: t.loadError,
        },
      }
    : undefined;

  const manage: KitchenManage = {
    kitchenId,
    name: kitchenTitle ?? "",
    isOwner,
    isArchived: Boolean(detail?.is_archived),
    isDefault: defaultKitchenId === kitchenId,
    locale,
  };

  return (
    <main className={styles.detailMain}>
      {notFound || !showKitchenDetail ? (
        <>
          <KitchenDetailChrome title={notFound ? t.detailNotFound : t.loadError} />
          <p className={styles.copy}>
            <Link className={styles.link} href="/home">
              {t.backToKitchens}
            </Link>
          </p>
        </>
      ) : (
        <KitchenCartCountProvider>
          <KitchenDetailChrome
            title={kitchenTitle as string}
            share={share}
            manage={manage}
            cart={{
              href: `/kitchens/${encodeURIComponent(kitchenId)}/cart`,
              label: cartMessages[locale].cart,
              locale,
            }}
          />
          <KitchenNotebooksSection
            kitchenId={kitchenId}
            isArchived={Boolean(detail?.is_archived)}
            locale={locale}
          />
        </KitchenCartCountProvider>
      )}
    </main>
  );
}
