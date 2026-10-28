"use client";

import { usePathname } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

export type ChromeHeaderConfig = {
  /** When set, AppShell renders a ghost Back IconButton that pushes this href. */
  backHref?: string | null;
  /** When set, Back runs this instead of pushing `backHref` (e.g. discard then navigate). */
  onBack?: (() => void) | null;
  /**
   * Replaces the Back button in the same fixed leading slot (e.g. an Avatar on
   * top-level tabs that have no back navigation). Ignored if `backHref`/`onBack`
   * is also set — Back takes priority.
   */
  leading?: ReactNode;
  title?: ReactNode;
  /** Short inline content next to the title (e.g. a status word or a count) — not for large/interactive elements. */
  details?: ReactNode;
  /**
   * Overrides the `details` chip's border/text color classes (e.g. `"border-owe text-owe"`
   * for an over-budget state) — full Tailwind classes, not limited to the fixed Chip tones.
   */
  detailsClassName?: string;
  trailing?: ReactNode;
  /**
   * Optional full-width strip rendered edge-to-edge above the header row,
   * outside the scrollable content area — stays visible while the page
   * scrolls (e.g. a `TopProgressBar`).
   */
  progressBar?: ReactNode | null;
};

const emptyHeader: ChromeHeaderConfig = {};

type HeaderEntry = { id: string; order: number; config: ChromeHeaderConfig };

type HeaderRegistry = {
  /**
   * Reserves this screen's place in the stack. Called while rendering, which visits a parent
   * before its children, so a screen nested inside another always ranks above it. Safe to call
   * again: the place is kept.
   */
  claim: (id: string) => void;
  /** Sets this screen's header at its place in the stack, and remembers its title for `route`. */
  upsert: (id: string, config: ChromeHeaderConfig, route: string) => void;
  /** Removes only this entry; the one beneath it shows again. */
  remove: (id: string) => void;
};

/** The title and Back target a route last showed, kept to fill in while its screen loads. */
type RememberedHeader = Pick<ChromeHeaderConfig, "title" | "backHref">;

/** Routes remembered at most; the longest unused are forgotten first. */
const REMEMBERED_ROUTES_MAX = 50;

const ChromeHeaderContext = createContext<ChromeHeaderConfig>(emptyHeader);
const ChromeHeaderRegistryContext = createContext<HeaderRegistry | null>(null);
/** The route being shown. The registry stays the same across routes; this changes. */
const ChromeRouteContext = createContext<string>("");

/**
 * Owns AppShell's top nav. Screens opt in via `useChromeHeader` or `useChromeBack`.
 *
 * The header is a stack of entries, one per screen that asked for it; the top one is shown.
 * A screen ranks by when it first rendered, not by when its effects ran (a child's effects run
 * before its parent's, which would put a layout above its own page). A screen that mounts over
 * another (a nested layout and its page, or the next page while the previous one is still
 * unmounting) is above it, and when it unmounts it removes only its own entry, so the header
 * underneath comes back in the right order. Removing by id also makes the order of the old
 * screen's cleanup and the new screen's setup irrelevant: neither can blank the other's header.
 *
 * It also remembers the title of each route it has shown. Going Back to a server-rendered page
 * shows that page's loading state first, and until its own screen sets a title the header would
 * be blank; the remembered title is shown for that while, and the real one replaces it.
 */
export function ChromeBackProvider({ children }: { children: ReactNode }) {
  const route = usePathname() ?? "";
  const [entries, setEntries] = useState<HeaderEntry[]>([]);
  const [remembered, setRemembered] = useState<Record<string, RememberedHeader>>({});
  const orders = useRef(new Map<string, number>());
  const nextOrder = useRef(0);

  const claim = useCallback((id: string) => {
    if (!orders.current.has(id)) orders.current.set(id, nextOrder.current++);
  }, []);
  const upsert = useCallback(
    (id: string, config: ChromeHeaderConfig, forRoute: string) => {
      claim(id);
      const order = orders.current.get(id) as number;
      if (config.title) {
        setRemembered((current) => {
          const known = current[forRoute];
          if (known && known.title === config.title && known.backHref === config.backHref) {
            return current;
          }
          // Re-added last, so the oldest routes are the ones dropped when there are too many.
          const others = Object.entries(current).filter(([key]) => key !== forRoute);
          const kept = others.slice(-(REMEMBERED_ROUTES_MAX - 1));
          return {
            ...Object.fromEntries(kept),
            [forRoute]: { title: config.title, backHref: config.backHref },
          };
        });
      }
      setEntries((current) => {
        const index = current.findIndex((entry) => entry.id === id);
        if (index === -1) return [...current, { id, order, config }];
        const next = current.slice();
        next[index] = { id, order, config };
        return next;
      });
    },
    [claim],
  );
  const remove = useCallback((id: string) => {
    orders.current.delete(id);
    setEntries((current) =>
      current.some((entry) => entry.id === id)
        ? current.filter((entry) => entry.id !== id)
        : current,
    );
  }, []);
  const registry = useMemo(() => ({ claim, upsert, remove }), [claim, upsert, remove]);

  const top = entries.reduce<HeaderEntry | null>(
    (best, entry) => (best === null || entry.order > best.order ? entry : best),
    null,
  );
  const shown = top ? top.config : emptyHeader;
  const known = remembered[route];
  const header = useMemo(
    () =>
      shown.title || !known
        ? shown
        : { ...shown, title: known.title, backHref: shown.backHref ?? known.backHref },
    [shown, known],
  );
  return (
    <ChromeHeaderRegistryContext.Provider value={registry}>
      <ChromeRouteContext.Provider value={route}>
        <ChromeHeaderContext.Provider value={header}>{children}</ChromeHeaderContext.Provider>
      </ChromeRouteContext.Provider>
    </ChromeHeaderRegistryContext.Provider>
  );
}

export function useChromeHeaderState(): ChromeHeaderConfig {
  return useContext(ChromeHeaderContext);
}

export function chromeHeaderIsActive(header: ChromeHeaderConfig): boolean {
  return Boolean(
    header.backHref ||
      header.onBack ||
      header.leading ||
      header.title ||
      header.details ||
      header.trailing,
  );
}

/**
 * Opt-in: while this screen is mounted, it has an entry in AppShell's header stack, and the
 * entry on top drives the top nav. No-op if the provider is not in the tree (e.g. isolated
 * panel tests).
 */
export function useChromeHeader(config: ChromeHeaderConfig) {
  const registry = useContext(ChromeHeaderRegistryContext);
  const routeNow = useContext(ChromeRouteContext);
  // The route this screen mounted for. A screen only ever remembers its title under that route,
  // even if it is still unmounting after the address has already moved on.
  const [route] = useState(() => routeNow);
  const id = useId();
  // Render visits a parent before its children: this is what ranks a nested screen above its parent.
  registry?.claim(id);
  const {
    backHref,
    onBack,
    leading,
    title,
    details,
    detailsClassName,
    trailing,
    progressBar,
  } = config;

  // A change to this screen's own header updates its entry where it is; it never moves it to
  // the top, so a screen below another one cannot take the header from it.
  useEffect(() => {
    if (!registry) return;
    registry.upsert(
      id,
      {
        backHref,
        onBack,
        leading,
        title,
        details,
        detailsClassName,
        trailing,
        progressBar,
      },
      route,
    );
  }, [
    registry,
    id,
    route,
    backHref,
    onBack,
    leading,
    title,
    details,
    detailsClassName,
    trailing,
    progressBar,
  ]);

  // Only unmounting removes the entry.
  useEffect(() => {
    if (!registry) return;
    return () => registry.remove(id);
  }, [registry, id]);
}

export function useChromeBackHref(): string | null {
  return useContext(ChromeHeaderContext).backHref ?? null;
}

/**
 * Opt-in: while this screen is mounted, show AppShell's Back control
 * and navigate to `href` on click. Prefer `useChromeHeader` when the
 * screen also has a title, details, or trailing actions.
 */
export function useChromeBack(href: string) {
  useChromeHeader({ backHref: href });
}
