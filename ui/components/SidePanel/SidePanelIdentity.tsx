"use client";

import { PencilIcon, TrashIcon } from "@/app/icons";
import { Avatar } from "@/components/Avatar";
import { AvatarCropSheet } from "@/components/AvatarCropSheet";
import { usePreferences } from "@/components/PreferencesProvider";
import { Tooltip } from "@/components/Tooltip";
import { accountCopy } from "@/lib/i18n/account";
import { PANEL_SLIDE, usePanelLayout } from "./panelLayout";
import { useProfilePhoto } from "./useProfilePhoto";

const photoActionClass =
  "absolute inline-flex size-6 items-center justify-center rounded-full border border-border bg-surface text-foreground cursor-pointer shadow-sm disabled:opacity-45 disabled:cursor-not-allowed";

/** Avatar with its photo edits, alias and recipe count. Edits and text need the wide panel. */
export function SidePanelIdentity({
  recipeCount,
  notebookCount,
}: {
  recipeCount: string | null;
  notebookCount: string | null;
}) {
  const { wide, openOnlyClass } = usePanelLayout();
  const { me, locale } = usePreferences();
  const t = accountCopy(locale);
  const photo = useProfilePhoto(t.photoError);

  return (
    <div className="mb-2 flex h-20 items-center gap-3 px-2">
      <div
        className={`relative flex aspect-square shrink-0 transition-[width] ${PANEL_SLIDE} ${wide ? "w-16" : "w-16 md:w-7"}`}
      >
        <Avatar
          alias={me?.alias ?? null}
          seed={me?.user_id ?? "account"}
          photoBase64={me?.photo_base64 ?? null}
          fluid
          className={`transition-[font-size] ${PANEL_SLIDE} ${wide ? "text-[1.75rem]" : "text-[1.75rem] md:text-[0.75rem]"}`}
        />
        <div className={openOnlyClass}>
          <label className={`${photoActionClass} -bottom-1.5 -left-1.5`}>
            <Tooltip label={t.photoUpload}>
              <PencilIcon className="size-3.5" />
            </Tooltip>
            <input
              type="file"
              accept="image/png,image/jpeg"
              aria-label={t.photoUpload}
              className="hidden"
              disabled={photo.pending}
              onChange={photo.onPick}
            />
          </label>
          {me?.photo_base64 ? (
            <button
              type="button"
              aria-label={t.photoRemove}
              className={`${photoActionClass} -top-1.5 -right-1.5 text-owe`}
              disabled={photo.pending}
              onClick={() => void photo.save(null)}
            >
              <Tooltip label={t.photoRemove}>
                <TrashIcon className="size-3.5" />
              </Tooltip>
            </button>
          ) : null}
        </div>
      </div>
      <div
        data-side-panel="identity"
        className={`min-w-0 flex-1 ${openOnlyClass}`}
      >
        <p className="m-0 truncate text-[0.95rem] font-semibold leading-tight text-foreground">
          {me?.alias ?? ""}
        </p>
        {recipeCount ? (
          <p className="m-0 mt-0.5 text-[0.8rem] text-muted">{recipeCount}</p>
        ) : null}
        {notebookCount ? (
          <p className="m-0 text-[0.8rem] text-muted">{notebookCount}</p>
        ) : null}
        {photo.error ? (
          <p className="m-0 mt-1 text-[0.8rem] text-owe">{photo.error}</p>
        ) : null}
      </div>
      <AvatarCropSheet
        file={photo.cropFile}
        open={photo.cropOpen}
        onClose={photo.closeCrop}
        onConfirm={(dataUri) => void photo.save(dataUri)}
        onError={photo.failCrop}
        title={t.photoCropTitle}
        saveLabel={t.photoCropSave}
        closeLabel={t.photoCropCancel}
        zoomLabel={t.photoCropZoom}
      />
    </div>
  );
}
