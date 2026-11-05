"use client";

import { useRef, useState, type ChangeEvent } from "react";

import { PencilIcon, TrashIcon, UploadIcon } from "@/app/icons";
import { AvatarCropSheet } from "@/components/AvatarCropSheet";
import { IconButton } from "@/components/IconButton";
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
        <figure className="relative m-0 self-start">
          {/* eslint-disable-next-line @next/next/no-img-element -- a data URI, not a site address */}
          <img
            src={value}
            alt={t.recipePhotoAlt}
            className="block max-h-56 max-w-full rounded-[0.75rem] object-cover"
          />
          <span className="absolute top-2 right-2 flex gap-1">
            <IconButton
              variant="ghost"
              label={t.changePhoto}
              icon={<PencilIcon className="size-5" />}
              onClick={pick}
              disabled={disabled}
              className="bg-background/80"
            />
            <IconButton
              variant="ghost"
              label={t.removePhoto}
              icon={<TrashIcon className="size-5" />}
              onClick={() => onChange(null)}
              disabled={disabled}
              className="bg-background/80"
            />
          </span>
        </figure>
      ) : (
        <button
          type="button"
          onClick={pick}
          disabled={disabled}
          className="flex items-center gap-2 self-start rounded-[0.75rem] border border-dashed border-border px-4 py-3 text-[0.9rem] text-muted hover:text-foreground disabled:opacity-50"
        >
          <UploadIcon className="size-5" />
          {t.addPhoto}
        </button>
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
