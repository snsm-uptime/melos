"use client";

import { useRef, useState, type ChangeEvent } from "react";

import { PencilIcon, PotIcon, TrashIcon, UploadIcon } from "@/app/icons";
import { AvatarCropSheet } from "@/components/AvatarCropSheet";
import { AddItemCard } from "@/components/Card";
import { IconButton } from "@/components/IconButton";
import { photoActionClass } from "@/components/photoAction";
import { Tooltip } from "@/components/Tooltip";
import { captureMessagesFor } from "@/lib/i18n/capture";
import type { Locale } from "@/lib/i18n/locale";
import { encodeCroppedRecipeImage } from "@/lib/imageEncode";

/** The recipe photo's shape: wider than tall, like the cards and the detail. */
const RECIPE_IMAGE_ASPECT = 4 / 3;

type RecipeImagePickerProps = {
  /** The image as a data URI, or null for none. */
  value: string | null;
  /** A new cropped image, or null when the person removes it. */
  onChange: (value: string | null) => void;
  locale: Locale;
  disabled?: boolean;
  /**
   * With no image: "placeholder" shows the cards' pot placeholder with an upload button (the
   * draft); "add" shows the shared add-item card (the edit page).
   */
  empty?: "placeholder" | "add";
};

/**
 * Pick, crop and remove a recipe's photo (S-067), on the draft and the edit page. The same
 * pick-then-crop flow as the profile photo; the crop is a 4:3 rectangle, shrunk in the
 * browser to the api's limit (longest side 800 px, JPEG, under 300 KB).
 */
export function RecipeImagePicker({
  value,
  onChange,
  locale,
  disabled = false,
  empty = "placeholder",
}: RecipeImagePickerProps) {
  const t = captureMessagesFor(locale);
  const input = useRef<HTMLInputElement>(null);
  const [cropFile, setCropFile] = useState<File | null>(null);
  const [cropOpen, setCropOpen] = useState(false);
  const [failed, setFailed] = useState(false);

  function onPick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setFailed(false);
    setCropFile(file);
    setCropOpen(true);
  }

  const pick = () => input.current?.click();
  // The edit page's slot is one height with or without a photo, so adding or removing one does
  // not move the form below it. The draft keeps its own sizes.
  const fixedSlot = empty === "add";

  return (
    <div className="flex flex-col gap-2">
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        aria-hidden="true"
        tabIndex={-1}
        onChange={onPick}
      />
      {value ? (
        // The detail page's image: full column width, at most 18rem tall.
        <figure className="relative m-0">
          {/* eslint-disable-next-line @next/next/no-img-element -- a data URI, not a site address */}
          <img
            src={value}
            alt={t.recipePhotoAlt}
            className={`block w-full rounded-[0.75rem] object-cover ${fixedSlot ? "h-72" : "max-h-72"}`}
          />
          {/* The avatar's photo actions: change on the bottom-left corner, remove on the top-right. */}
          <button
            type="button"
            aria-label={t.changePhoto}
            className={`${photoActionClass} bottom-2 left-2 size-8`}
            disabled={disabled}
            onClick={pick}
          >
            <Tooltip label={t.changePhoto}>
              <PencilIcon className="size-4" />
            </Tooltip>
          </button>
          <button
            type="button"
            aria-label={t.removePhoto}
            className={`${photoActionClass} top-2 right-2 size-8 text-error`}
            disabled={disabled}
            onClick={() => onChange(null)}
          >
            <Tooltip label={t.removePhoto}>
              <TrashIcon className="size-4" />
            </Tooltip>
          </button>
        </figure>
      ) : empty === "add" ? (
        <AddItemCard label={t.addPhoto} onClick={pick} disabled={disabled} className="h-72" />
      ) : (
        // The cards' placeholder, at the detail image's size.
        <div className="relative">
          <span
            data-testid="recipe-image-placeholder"
            className="flex h-56 w-full items-center justify-center rounded-[var(--radius-md)] border border-border bg-surface text-muted"
          >
            <PotIcon />
          </span>
          <span className="absolute top-2 right-2">
            <IconButton
              variant="ghost"
              label={t.addPhoto}
              icon={<UploadIcon className="size-5" />}
              onClick={pick}
              disabled={disabled}
            />
          </span>
        </div>
      )}
      {failed ? (
        <p role="alert" className="m-0 text-[0.85rem] text-error">
          {t.photoFailed}
        </p>
      ) : null}
      <AvatarCropSheet
        file={cropFile}
        open={cropOpen}
        onClose={() => setCropOpen(false)}
        onConfirm={onChange}
        onError={() => setFailed(true)}
        title={t.photoCropTitle}
        saveLabel={t.photoCropSave}
        closeLabel={t.close}
        zoomLabel={t.photoCropZoom}
        aspect={RECIPE_IMAGE_ASPECT}
        cropShape="rect"
        encode={(img, area) => encodeCroppedRecipeImage(img, area)}
      />
    </div>
  );
}
