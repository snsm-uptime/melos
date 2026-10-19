"use client";

import { useChromeHeader } from "@/components/ChromeBack";

/** Opts kitchen detail into AppShell Back + title. */
export function KitchenDetailChrome({ title }: { title: string }) {
  useChromeHeader({
    backHref: "/home",
    title,
  });
  return null;
}
