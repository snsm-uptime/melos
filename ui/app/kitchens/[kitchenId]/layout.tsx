"use client";

import type { ReactNode } from "react";
import { useChromeHeader } from "@/components/ChromeBack";

/**
 * Persists across the loading.tsx -> page.tsx swap for this route segment, so
 * Back shows immediately instead of waiting for the page's server fetch to
 * resolve. KitchenDetailChrome overwrites this with the title
 * once the kitchen data is available.
 */
export default function KitchenDetailLayout({ children }: { children: ReactNode }) {
  useChromeHeader({ backHref: "/home" });
  return children;
}
