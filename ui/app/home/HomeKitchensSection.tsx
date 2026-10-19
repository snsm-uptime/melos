"use client";

import { useState } from "react";

import { KitchensPanel } from "@/app/kitchens/KitchensPanel";
import type { KitchenItem } from "@/app/kitchens/kitchensClient";
import { HomeChrome } from "./HomeChrome";

type Props = {
  title: string;
  alias: string | null;
  userId: string;
  photoBase64: string | null;
  initialKitchens: KitchenItem[];
  currentUserId: string;
};

/**
 * Owns the archived-kitchens toggle state shared between the chrome (renders
 * the box icon) and the panel (filters what's shown) — `HomeChrome` and
 * `KitchensPanel` are independent sibling client components under the Server
 * Component `page.tsx`, so the toggle state has to live in a shared parent
 * rather than in either sibling. Unmounting this component (navigating away
 * from Home) drops the state, satisfying "reverts to OFF on navigate away"
 * (Story 9.2 AC #4) with no extra reset code.
 */
export function HomeKitchensSection({
  title,
  alias,
  userId,
  photoBase64,
  initialKitchens,
  currentUserId,
}: Props) {
  const [showArchived, setShowArchived] = useState(false);
  return (
    <>
      <HomeChrome
        title={title}
        alias={alias}
        userId={userId}
        photoBase64={photoBase64}
        showArchived={showArchived}
        onToggleArchived={() => setShowArchived((prev) => !prev)}
      />
      <KitchensPanel
        initialKitchens={initialKitchens}
        currentUserId={currentUserId}
        showArchived={showArchived}
      />
    </>
  );
}
