"use client";

import { useEffect, useState } from "react";

import { getCaptureState, takeSavedNotice } from "@/lib/capture/captureStore";
import { captureMessages } from "@/lib/i18n/capture";

/**
 * "Recipe saved", shown once on the page a successful Save returned to (spec 020 FR-014).
 * Reading the notice clears it, so a reload or another visit shows nothing.
 */
export function SavedNotice({ returnPath }: { returnPath: string }) {
  const [shown] = useState(() => getCaptureState().savedNotice?.returnPath === returnPath);
  useEffect(() => {
    takeSavedNotice(returnPath);
  }, [returnPath]);
  if (!shown) return null;
  return (
    <p role="status" className="rounded-[0.75rem] bg-surface px-3 py-2 text-[0.9rem] text-foreground">
      {captureMessages.saved}
    </p>
  );
}
