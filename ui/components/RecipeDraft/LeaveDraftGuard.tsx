"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ActionDialog } from "@/components/ActionDialog/ActionDialog";
import {
  clearCapture,
  isDraftEdited,
  useCaptureState,
} from "@/lib/capture/captureStore";
import { captureMessages } from "@/lib/i18n/capture";

/**
 * Asks before a leave that would lose an edited draft (spec 016 FR-032). Back and Discard do
 * not come through here. Only an edited draft is guarded, and a reload gets the browser's warning.
 */
export function LeaveDraftGuard() {
  const router = useRouter();
  const capture = useCaptureState();
  const edited = isDraftEdited(capture);
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
      const anchor = target?.closest?.("a[href]") as
        HTMLAnchorElement | null | undefined;
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
      title={captureMessages.leaveTitle}
      confirmLabel={captureMessages.leave}
      cancelLabel={captureMessages.stay}
      onOpenChange={(open) => {
        if (!open) setPendingHref(null);
      }}
      onConfirm={() => {
        const target = pendingHref;
        setPendingHref(null);
        clearCapture();
        if (target) router.push(target);
      }}
    >
      <p className="m-0 text-[0.95rem] text-muted">
        {captureMessages.leaveBody}
      </p>
    </ActionDialog>
  );
}
