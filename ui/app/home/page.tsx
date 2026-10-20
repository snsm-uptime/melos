import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { requireAlias } from "@/lib/alias";
import { getApiInternalUrl } from "@/lib/api";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import type { Locale } from "@/lib/i18n/locale";
import { fetchSession } from "@/lib/session";
import type { KitchenItem } from "@/app/kitchens/kitchensClient";
import kitchensStyles from "@/app/kitchens/kitchens.module.scss";
import { HomeChrome } from "./HomeChrome";
import { HomeKitchensSection } from "./HomeKitchensSection";

export const dynamic = "force-dynamic";

type MembershipLoad =
  | { ok: true; kitchens: KitchenItem[] }
  | { ok: false };

async function fetchMembershipKitchens(): Promise<MembershipLoad> {
  const jar = await cookies();
  const cookieHeader = jar
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  try {
    const response = await fetch(`${getApiInternalUrl()}/kitchens`, {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...(cookieHeader ? { Cookie: cookieHeader } : {}),
      },
      cache: "no-store",
    });
    if (!response.ok) return { ok: false };
    const data = (await response.json()) as { kitchens?: KitchenItem[] };
    if (!Array.isArray(data.kitchens)) return { ok: false };
    return { ok: true, kitchens: data.kitchens };
  } catch {
    return { ok: false };
  }
}

function resolvePageLocale(languageCookie: string | undefined): Locale {
  if (languageCookie === "es" || languageCookie === "en") return languageCookie;
  return "en";
}

/** Home: Kitchens only — Cards moved to its own /cards route. */
export default async function Home() {
  const session = await fetchSession();
  if (!session) {
    redirect("/sign-in?returnTo=/home");
  }
  // No kitchen chrome without an alias — redirects to setup on first signed-in visit.
  const me = await requireAlias("/home");

  const jar = await cookies();
  const locale = resolvePageLocale(jar.get("melos_lang_cache")?.value);
  const t = kitchensMessages[locale];
  const loaded = await fetchMembershipKitchens();

  if (!loaded.ok) {
    return (
      <main className={kitchensStyles.main}>
        <HomeChrome
          title={t.title}
          alias={me.alias}
          userId={me.user_id}
          photoBase64={me.photo_base64}
        />
        <p className={kitchensStyles.error} role="alert">
          {t.loadError}
        </p>
      </main>
    );
  }

  return (
    <main className={kitchensStyles.main}>
      <HomeKitchensSection
        title={t.title}
        alias={me.alias}
        userId={me.user_id}
        photoBase64={me.photo_base64}
        initialKitchens={loaded.kitchens}
        currentUserId={session.user_id}
      />
    </main>
  );
}
