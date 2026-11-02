import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { requireAlias } from "@/lib/alias";
import { getApiInternalUrl } from "@/lib/api";
import { asCart, type Cart } from "@/lib/cartClient";
import { cartMessages } from "@/lib/i18n/cart";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { notebooksMessages } from "@/lib/i18n/notebooks";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import { readListAddress } from "@/lib/listAddress";
import { asNotebookList, type NotebookResponse } from "@/lib/notebooksClient";
import { asPage, type RecipePage } from "@/lib/recipesClient";
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

/** Null on any failure: the section then reads it itself and shows its own error and retry. */
async function readOptional<T>(
  path: string,
  init: RequestInit,
  parse: (data: unknown) => T | null,
): Promise<T | null> {
  try {
    const response = await fetch(`${getApiInternalUrl()}${path}`, init);
    return response.ok ? parse(await response.json()) : null;
  } catch {
    return null;
  }
}

export default async function KitchenDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ kitchenId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { kitchenId } = await params;
  const query = await searchParams;
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
  let notebooks: NotebookResponse[] | null = null;
  let recipes: RecipePage | null = null;
  let cart: Cart | null = null;
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
      const path = `/kitchens/${encodeURIComponent(kitchenId)}`;
      const { page, q } = readListAddress({
        get: (name) => (typeof query[name] === "string" ? query[name] : null),
      });
      const recipeQuery = new URLSearchParams({ page: String(page) });
      if (q.trim()) recipeQuery.set("q", q);
      // Read everything the section shows here, so the route's loader is the only wait.
      const [detailData, membersRes, panelRes, notebooksData, recipesData, cartData] = await Promise.all([
        response.json() as Promise<DetailPayload>,
        fetch(`${getApiInternalUrl()}/kitchens/${encodeURIComponent(kitchenId)}/members`, requestInit),
        fetch(`${getApiInternalUrl()}/side-panel`, requestInit),
        readOptional(`/notebooks${path}`, requestInit, asNotebookList),
        readOptional(`/notebooks${path}/recipes?${recipeQuery}`, requestInit, asPage),
        readOptional(`${path}/cart`, requestInit, asCart),
      ]);
      notebooks = notebooksData;
      recipes = recipesData;
      cart = cartData;
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
    <main className={`${styles.detailMain} flex-1`}>
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
            pastLists={{
              href: `/kitchens/${encodeURIComponent(kitchenId)}/shopping-lists`,
              label: shoppingListMessages[locale].pastLists,
            }}
            notebooks={{
              href: `/kitchens/${encodeURIComponent(kitchenId)}/notebooks`,
              label: notebooksMessages[locale].openNotebooks,
            }}
          />
          <KitchenNotebooksSection
            kitchenId={kitchenId}
            isArchived={Boolean(detail?.is_archived)}
            locale={locale}
            initialNotebooks={notebooks ?? undefined}
            initialRecipes={recipes ?? undefined}
            initialCart={cart ?? undefined}
          />
        </KitchenCartCountProvider>
      )}
    </main>
  );
}
