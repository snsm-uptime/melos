"use client";

import { LeaveDraftGuard } from "./LeaveDraftGuard";
import { RecipeDraftEditor } from "./RecipeDraftEditor";
import { captureMessages } from "@/lib/i18n/capture";

/** The full-screen draft review page: the header, the editor and the leave guard (FR-032). */
export function RecipeDraftPage() {
  return (
    <main className="mx-auto flex w-full max-w-[40rem] flex-col gap-4 px-4 py-6">
      <h1 className="m-0 text-[1.25rem] font-[550] text-foreground">{captureMessages.reviewTitle}</h1>
      <RecipeDraftEditor />
      <LeaveDraftGuard />
    </main>
  );
}
