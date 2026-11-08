"use client";

import { useEffect, useRef } from "react";

import { useOptionalPreferences } from "@/components/PreferencesProvider";
import { useToast } from "@/components/Toast";
import type { DraftView } from "@/lib/capture/captureStore";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";

/** The id of the picture disclaimer toast: one on screen at a time (spec 041, FR-013c). */
export const PICTURE_DISCLAIMER_TOAST = "picture-disclaimer";

/** How long the disclaimer stays (spec 041): ten seconds, closable by a tap. */
const DISCLAIMER_MS = 10_000;

/**
 * The picture draft's disclaimer toast (spec 041, FR-013c). Shown once per draft, keyed by its
 * save key so later edits do not show it again. Shown only when the account keeps the option on,
 * and never while preferences are still loading. Leaving the page dismisses it.
 */
export function usePictureDisclaimer(draft: DraftView | null, saveKey: string | null): void {
  const prefs = useOptionalPreferences();
  const toast = useToast();
  const t = useCaptureMessages();
  const shownFor = useRef<string | null>(null);

  const fromPicture = draft?.fromPicture === true;
  const ready = prefs?.ready === true;
  const keepsDisclaimer = prefs?.me?.disclaimers !== false;
  const text = t.pictureDisclaimer;

  useEffect(() => {
    if (!fromPicture || !saveKey || !ready || !keepsDisclaimer) return;
    if (shownFor.current === saveKey) return;
    shownFor.current = saveKey;
    toast.show({ id: PICTURE_DISCLAIMER_TOAST, text, durationMs: DISCLAIMER_MS });
  }, [fromPicture, saveKey, ready, keepsDisclaimer, text, toast]);

  useEffect(() => () => toast.dismiss(PICTURE_DISCLAIMER_TOAST), [toast]);
}
