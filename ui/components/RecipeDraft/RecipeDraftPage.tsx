"use client";

import { useCaptureState } from "@/lib/capture/captureStore";

import { LeaveDraftGuard } from "./LeaveDraftGuard";
import { RecipeDraftEditor } from "./RecipeDraftEditor";
import { usePictureDisclaimer } from "./usePictureDisclaimer";

/** The full-screen draft review page: the editor and the leave guard (FR-032). */
export function RecipeDraftPage() {
  const capture = useCaptureState();
  usePictureDisclaimer(capture.draft, capture.saveKey);
  return (
    <main className="mx-auto flex w-full flex-col gap-4 md:min-h-0 md:flex-1">
      <RecipeDraftEditor />
      <LeaveDraftGuard />
    </main>
  );
}
