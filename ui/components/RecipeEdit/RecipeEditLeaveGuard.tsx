"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ActionDialog } from "@/components/ActionDialog/ActionDialog";
import type { Locale } from "@/lib/i18n/locale";
import { recipeDetailMessages } from "@/lib/i18n/recipeDetail";

/**
 * Asks before a leave that would lose unsaved edits (spec 027 FR-012). Modeled on the draft's
 * LeaveDraftGuard but driven by the form, not the capture store. Back and Cancel are links, so
 * they pass through the same click check; a reload or tab close gets the browser's warning.
 */
export function RecipeEditLeaveGuard({ edited, locale }: { edited: boolean; locale: Locale }) {
  const t = recipeDetailMessages[locale];
  const router = useRouter();
  const [pendingHref, setPendingHref] = useState<string | null>(null);

  useEffect(() => {
    if (!edited) return;
    function onBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = "";
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [edited]);

  useEffect(() => {
    if (!edited) return;
    function onClick(event: MouseEvent) {
      const target = event.target as Element | null;
      const anchor = target?.closest?.("a[href]") as HTMLAnchorElement | null | undefined;
      if (!anchor) return;
      const url = new URL(anchor.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (url.pathname === window.location.pathname) return;
      event.preventDefault();
      event.stopPropagation();
      setPendingHref(`${url.pathname}${url.search}${url.hash}`);
    }
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, [edited]);

  return (
    <ActionDialog
      open={pendingHref !== null}
      title={t.leaveTitle}
      confirmLabel={t.leave}
      cancelLabel={t.stay}
      onOpenChange={(open) => {
        if (!open) setPendingHref(null);
      }}
      onConfirm={() => {
        const target = pendingHref;
        setPendingHref(null);
        if (target) router.push(target);
      }}
    >
      <p className="m-0 text-[0.95rem] text-muted">{t.leaveBody}</p>
    </ActionDialog>
  );
}
