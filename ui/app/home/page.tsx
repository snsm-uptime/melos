import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { requireAlias } from "@/lib/alias";
import { getApiInternalUrl } from "@/lib/api";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { fetchSession } from "@/lib/session";
import kitchensStyles from "@/app/kitchens/kitchens.module.scss";
import { getServerLocale } from "@/lib/serverLocale";
import { NoKitchensPrompt } from "./NoKitchensPrompt";

export const dynamic = "force-dynamic";

type DefaultLoad = { ok: true; kitchenId: string | null } | { ok: false };

async function fetchDefaultKitchen(): Promise<DefaultLoad> {
  const jar = await cookies();
  const cookieHeader = jar
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  try {
    const response = await fetch(`${getApiInternalUrl()}/side-panel`, {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...(cookieHeader ? { Cookie: cookieHeader } : {}),
      },
      cache: "no-store",
    });
    if (!response.ok) return { ok: false };
    const data = (await response.json()) as { default_kitchen_id?: string | null };
    return { ok: true, kitchenId: data.default_kitchen_id ?? null };
  } catch {
    return { ok: false };
  }
}

/** Home opens the default kitchen; with no kitchens it offers to create one (spec 064 R7). */
export default async function Home() {
  const session = await fetchSession();
  if (!session) {
    redirect("/sign-in?returnTo=/home");
  }
  // No kitchen chrome without an alias — redirects to setup on first signed-in visit.
  await requireAlias("/home");

  const loaded = await fetchDefaultKitchen();
  if (loaded.ok && loaded.kitchenId) {
    redirect(`/kitchens/${encodeURIComponent(loaded.kitchenId)}`);
  }

  const t = kitchensMessages[await getServerLocale()];
  return (
    <main className={kitchensStyles.main}>
      {loaded.ok ? (
        <NoKitchensPrompt />
      ) : (
        <p className={kitchensStyles.error} role="alert">
          {t.loadError}
        </p>
      )}
    </main>
  );
}
