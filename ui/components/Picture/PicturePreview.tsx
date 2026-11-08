"use client";

import { ActionDialog } from "@/components/ActionDialog";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";

type PicturePreviewProps = {
  open: boolean;
  /** The recipe's stored preview (`preview_image`), a WebP data URI. Never an original upload. */
  src: string;
  title: string;
  onClose: () => void;
};

/**
 * The recipe's picture in a pop-up (spec 041, FR-027): shown at a size that fits the viewport.
 * It is a view only: no download link and no original image. Escape and the close control close it.
 */
export function PicturePreview({ open, src, title, onClose }: PicturePreviewProps) {
  const t = useCaptureMessages();
  return (
    <ActionDialog
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      closeLabel={t.close}
      title={title}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={t.picturePreviewAlt}
        className="mx-auto block max-h-[70vh] max-w-full rounded-[0.75rem] object-contain"
      />
    </ActionDialog>
  );
}
