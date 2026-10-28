import { cookies } from "next/headers";
import { cache } from "react";

import { fetchMe } from "@/lib/alias";
import { LANGUAGE_COOKIE, resolveLocale, type Locale } from "@/lib/i18n/locale";

/**
 * The interface language for a server-built page and for `<html lang>` (spec 063 research R1).
 * A signed-in account's saved language wins, even over a signed-out pick left in a cookie
 * (FR-018); with no account the pick cookie decides; otherwise the default, Spanish. A value
 * that is not English or Spanish counts as none (FR-016). Once per request.
 */
export const getServerLocale = cache(async (): Promise<Locale> => {
  const me = await fetchMe();
  if (me) return resolveLocale(me.language);
  const jar = await cookies();
  return resolveLocale(jar.get(LANGUAGE_COOKIE)?.value);
});
