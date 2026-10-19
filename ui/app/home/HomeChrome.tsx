"use client";

import { useChromeHeader } from "@/components/ChromeBack";
import { ChromeAvatarLink } from "@/components/ChromeAvatarLink";
import { IconButton } from "@/components/IconButton";
import { usePreferences } from "@/components/PreferencesProvider";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { ArchiveToggleIcon } from "@/app/icons";

/**
 * Opts Home into AppShell's chrome: avatar takes the leading slot (Home is a
 * top-level tab, so it has no back control to replace), title follows in the
 * standard chrome layout. Owns the archived-kitchens box-icon toggle (Story 9.2)
 * at the trailing end — optional so callers that don't
 * pass `onToggleArchived` (or existing tests) render the chrome without it.
 */
export function HomeChrome({
  title,
  alias,
  userId,
  photoBase64,
  showArchived = false,
  onToggleArchived,
}: {
  title: string;
  alias: string | null;
  userId: string;
  photoBase64: string | null;
  showArchived?: boolean;
  onToggleArchived?: () => void;
}) {
  const { locale } = usePreferences();
  const t = kitchensMessages[locale];
  useChromeHeader({
    leading: <ChromeAvatarLink alias={alias} userId={userId} photoBase64={photoBase64} />,
    title,
    trailing: onToggleArchived ? (
      <IconButton
        icon={<ArchiveToggleIcon active={showArchived} className="size-5" />}
        label={showArchived ? t.kitchensShowActive : t.kitchensShowArchived}
        aria-pressed={showArchived}
        onClick={onToggleArchived}
      />
    ) : undefined,
  });
  return null;
}
