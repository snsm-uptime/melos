"use client";

import { DotsIcon, PencilIcon, TrashIcon } from "@/app/icons";
import { IconButton } from "@/components/IconButton";
import { IconButtonPopup, IconButtonPopupItem } from "@/components/IconButtonPopup";
import type { Locale } from "@/lib/i18n/locale";
import { notebooksMessages } from "@/lib/i18n/notebooks";

/** The dots menu on a notebook's page, for those who may manage it (spec 059 research R8). */
export function NotebookOptionsMenu({
  locale,
  onRename,
  onDelete,
}: {
  locale: Locale;
  onRename: () => void;
  onDelete: () => void;
}) {
  const t = notebooksMessages[locale];
  return (
    <span className="inline-flex">
      <IconButtonPopup
        button={
          <IconButton
            type="button"
            variant="ghost"
            label={t.optionsLabel}
            icon={<DotsIcon className="size-6" />}
          />
        }
      >
        <IconButtonPopupItem onClick={onRename} icon={<PencilIcon />}>{t.renameAction}</IconButtonPopupItem>
        <IconButtonPopupItem danger onClick={onDelete} icon={<TrashIcon />}>
          {t.deleteAction}
        </IconButtonPopupItem>
      </IconButtonPopup>
    </span>
  );
}
