"use client";

import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState, type ReactNode, type RefObject } from "react";

/** Whether the app's main scroller has left its top. Read by the frosted bars (spec 072). */
const ChromeScrollContext = createContext(false);

/**
 * Wraps AppShell's main scroller and owns its one scroll listener. The value flips only when
 * `scrollTop > 0` changes, so a consumer re-renders on the flip and not on every scroll event.
 */
export function ChromeScrollProvider({
  scrollerRef,
  children,
}: {
  scrollerRef: RefObject<HTMLElement | null>;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return;
    const read = () => {
      const next = scroller.scrollTop > 0;
      setScrolled((prev) => (prev === next ? prev : next));
    };
    // The page can open already scrolled, and a new route starts at the top: read at mount and
    // on every route change.
    read();
    scroller.addEventListener("scroll", read, { passive: true });
    return () => scroller.removeEventListener("scroll", read);
  }, [scrollerRef, pathname]);

  return <ChromeScrollContext.Provider value={scrolled}>{children}</ChromeScrollContext.Provider>;
}

/** true once the main scroller has left its top; false at the top and outside a provider. */
export function useChromeScrolled(): boolean {
  return useContext(ChromeScrollContext);
}
