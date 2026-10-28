"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { clearLanguagePick, readLanguagePick, writeLanguagePick } from "@/lib/i18n/languagePick";
import {
  DEFAULT_LOCALE,
  isLocale,
  resolveLocale,
  type Locale,
  type ThemePreference,
} from "@/lib/i18n/locale";

const THEME_CACHE_KEY = "melos_theme_cache";

/** Bumped on sign-out / password-reset so in-flight GET refresh cannot rewrite cache. */
let prefsSessionEpoch = 0;
let prefsCacheWritesAllowed = true;

export function clearPrefsCache() {
  prefsSessionEpoch += 1;
  prefsCacheWritesAllowed = false;
  try {
    localStorage.removeItem(THEME_CACHE_KEY);
  } catch {
    /* ignore quota / private mode */
  }
}

export type MePreferences = {
  user_id: string;
  email: string;
  language: Locale | null;
  theme: ThemePreference | null;
  alias: string | null;
  photo_base64: string | null;
};

type PreferencesContextValue = {
  ready: boolean;
  locale: Locale;
  theme: ThemePreference;
  me: MePreferences | null;
  setTheme: (theme: ThemePreference) => Promise<void>;
  /**
   * Choose the interface language (spec 063). Signed in: saved to the account with
   * `PATCH /auth/me`, and rejects when it cannot be saved. Signed out: kept in the session pick
   * cookie. Either way the page and the server-built screens switch at once.
   */
  setLanguage: (locale: Locale) => Promise<void>;
  refresh: () => Promise<void>;
};

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

function resolveDarkClass(theme: ThemePreference): boolean {
  if (theme === "dark") return true;
  if (theme === "light") return false;
  if (typeof window === "undefined") return false;
  if (typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyDom(locale: Locale, theme: ThemePreference) {
  const root = document.documentElement;
  root.lang = locale;
  root.classList.remove("light", "dark");
  if (theme === "light") {
    root.classList.add("light");
  } else if (theme === "dark") {
    root.classList.add("dark");
  } else if (resolveDarkClass("system")) {
    root.classList.add("dark");
  }
  try {
    if (!prefsCacheWritesAllowed) return;
    localStorage.setItem(THEME_CACHE_KEY, theme);
  } catch {
    /* ignore quota / private mode */
  }
}

function resolveTheme(raw: string | null | undefined): ThemePreference {
  if (raw === "light" || raw === "dark" || raw === "system") return raw;
  return "system";
}

/** The router when the app router is mounted, null otherwise (component tests). */
function useOptionalRouter() {
  try {
    return useRouter();
  } catch {
    return null;
  }
}

export function PreferencesProvider({
  children,
  initialLocale = DEFAULT_LOCALE,
}: {
  children: ReactNode;
  /**
   * The language the server built the page in (`getServerLocale`). Starting from it keeps the
   * first browser render identical to the server HTML, so nothing flips (spec 063 FR-011).
   */
  initialLocale?: Locale;
}) {
  const router = useOptionalRouter();
  const [ready, setReady] = useState(false);
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const [theme, setThemeState] = useState<ThemePreference>("system");
  const [me, setMe] = useState<MePreferences | null>(null);
  const refreshGen = useRef(0);

  const refresh = useCallback(async () => {
    const gen = ++refreshGen.current;
    const epoch = prefsSessionEpoch;
    try {
      const response = await fetch("/api/auth/me", {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      if (gen !== refreshGen.current || epoch !== prefsSessionEpoch) return;
      if (!response.ok) {
        // Signed out: the pick made on a signed-out screen, else the default.
        const fallback = readLanguagePick() ?? DEFAULT_LOCALE;
        setMe(null);
        setLocale(fallback);
        setThemeState("system");
        applyDom(fallback, "system");
        return;
      }
      const data = (await response.json()) as {
        user_id?: string;
        email?: string;
        language?: string | null;
        theme?: string | null;
        alias?: string | null;
        photo_base64?: string | null;
      };
      if (gen !== refreshGen.current || epoch !== prefsSessionEpoch) return;
      const nextLocale = resolveLocale(data.language);
      const nextTheme = resolveTheme(data.theme);
      prefsCacheWritesAllowed = true;
      setMe({
        user_id: data.user_id ?? "",
        email: data.email ?? "",
        language:
          data.language === "es" || data.language === "en" ? data.language : null,
        theme:
          data.theme === "light" ||
          data.theme === "dark" ||
          data.theme === "system"
            ? data.theme
            : null,
        alias: typeof data.alias === "string" && data.alias ? data.alias : null,
        photo_base64:
          typeof data.photo_base64 === "string" && data.photo_base64 ? data.photo_base64 : null,
      });
      setLocale(nextLocale);
      setThemeState(nextTheme);
      applyDom(nextLocale, nextTheme);
    } catch {
      if (gen !== refreshGen.current || epoch !== prefsSessionEpoch) return;
      const fallback = readLanguagePick() ?? DEFAULT_LOCALE;
      setLocale(fallback);
      setThemeState("system");
      applyDom(fallback, "system");
    } finally {
      if (gen === refreshGen.current && epoch === prefsSessionEpoch) {
        setReady(true);
      }
    }
  }, []);

  useEffect(() => {
    // Hydrate from account API after mount (SoT is server, not localStorage).
    const handle = window.setTimeout(() => {
      void refresh();
    }, 0);
    return () => {
      window.clearTimeout(handle);
      refreshGen.current += 1;
    };
  }, [refresh]);

  useEffect(() => {
    if (theme !== "system") return;
    if (typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyDom(locale, "system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [theme, locale]);


  const setTheme = useCallback(async (next: ThemePreference) => {
    refreshGen.current += 1;
    const response = await fetch("/api/auth/me", {
      method: "PATCH",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ theme: next }),
    });
    if (!response.ok) {
      throw new Error("Failed to save theme");
    }
    const data = (await response.json()) as {
      language?: string | null;
      theme?: string | null;
      user_id?: string;
      email?: string;
      alias?: string | null;
      photo_base64?: string | null;
    };
    const nextLocale = resolveLocale(data.language);
    const nextTheme = resolveTheme(data.theme);
    setLocale(nextLocale);
    setThemeState(nextTheme);
    setMe({
      user_id: data.user_id ?? "",
      email: data.email ?? "",
      language:
        data.language === "es" || data.language === "en" ? data.language : null,
      theme:
        data.theme === "light" ||
        data.theme === "dark" ||
        data.theme === "system"
          ? data.theme
          : null,
      alias: typeof data.alias === "string" && data.alias ? data.alias : null,
      photo_base64:
        typeof data.photo_base64 === "string" && data.photo_base64 ? data.photo_base64 : null,
    });
    applyDom(nextLocale, nextTheme);
  }, []);

  const setLanguage = useCallback(
    async (next: Locale) => {
      if (me === null) {
        // Signed out: the pick lives in a session cookie the server can read on the next request.
        writeLanguagePick(next);
        setLocale(next);
        document.documentElement.lang = next;
        router?.refresh();
        return;
      }
      refreshGen.current += 1;
      const response = await fetch("/api/auth/me", {
        method: "PATCH",
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ language: next }),
      });
      if (!response.ok) {
        throw new Error("Failed to save language");
      }
      const data = (await response.json()) as { language?: string | null };
      const saved = isLocale(data.language) ? data.language : next;
      setMe((current) => (current ? { ...current, language: saved } : current));
      setLocale(saved);
      document.documentElement.lang = saved;
      clearLanguagePick();
      router?.refresh();
    },
    [me, router],
  );

  const value = useMemo(
    () => ({
      ready,
      locale,
      theme,
      me,
      setTheme,
      setLanguage,
      refresh,
    }),
    [ready, locale, theme, me, setTheme, setLanguage, refresh],
  );

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
}

/** Null outside a PreferencesProvider (e.g. component tests) instead of throwing —
 * callers that only want a soft default can treat a null context as "not loaded yet". */
export function useOptionalPreferences(): PreferencesContextValue | null {
  return useContext(PreferencesContext);
}

export function usePreferences(): PreferencesContextValue {
  const ctx = useContext(PreferencesContext);
  if (!ctx) {
    throw new Error("usePreferences must be used within PreferencesProvider");
  }
  return ctx;
}

/** Inline FOUC script for the theme — cache only; the account API remains source of truth. The language comes from the server (`<html lang>`). */
export const themeBootScript = `(function(){try{var t=localStorage.getItem('${THEME_CACHE_KEY}')||'system';var r=document.documentElement;r.classList.remove('light','dark');if(t==='light'){r.classList.add('light');}else if(t==='dark'){r.classList.add('dark');}else if(window.matchMedia('(prefers-color-scheme: dark)').matches){r.classList.add('dark');}}catch(e){}})();`;
