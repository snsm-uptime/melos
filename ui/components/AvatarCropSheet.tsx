"use client";

import { useEffect, useMemo, useState } from "react";
import Cropper, { type Area, type Point } from "react-easy-crop";

import { Sheet } from "@/app/kitchens/Sheet";
import { FormIconSubmit } from "@/components/FormIconSubmit/FormIconSubmit";
import {
  encodeCroppedAvatar,
  loadImage,
  type Area as EncodeArea,
} from "@/lib/imageEncode";

function encodeAvatar(
  img: HTMLImageElement,
  area: EncodeArea,
  file: File,
): Promise<string> {
  const mimeType = file.type === "image/png" ? "image/png" : "image/jpeg";
  return encodeCroppedAvatar(img, area, mimeType);
}

type Props = {
  /** The file the user just picked — drives the object URL fed to the cropper. */
  file: File | null;
  open: boolean;
  onClose: () => void;
  /** Called with the cropped, encoded data URI once the user confirms. */
  onConfirm: (dataUri: string) => void;
  /** Called if reading/encoding the image throws — caller shows its own copy. */
  onError: () => void;
  title: string;
  saveLabel: string;
  closeLabel: string;
  zoomLabel: string;
  /** Width over height of the crop; the avatar's square by default. */
  aspect?: number;
  cropShape?: "round" | "rect";
  /** Turns the cropped area into the data URI; the 256x256 avatar by default. */
  encode?: (img: HTMLImageElement, area: Area, file: File) => Promise<string>;
};

type CropEditorProps = Omit<Props, "file"> & {
  file: File;
  objectUrl: string;
};

/**
 * Keyed by `objectUrl` from the parent so crop/zoom state starts fresh for
 * every newly picked file (and every reopen) without an effect-driven reset.
 */
function CropEditor({
  file,
  objectUrl,
  open,
  onClose,
  onConfirm,
  onError,
  title,
  saveLabel,
  closeLabel,
  zoomLabel,
  aspect = 1,
  cropShape = "round",
  encode = encodeAvatar,
}: CropEditorProps) {
  const [crop, setCrop] = useState<Point>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null);
  const [confirming, setConfirming] = useState(false);

  async function handleConfirm() {
    if (!croppedAreaPixels || confirming) return;
    setConfirming(true);
    try {
      const img = await loadImage(file);
      const dataUri = await encode(img, croppedAreaPixels, file);
      onConfirm(dataUri);
      onClose();
    } catch {
      onError();
    } finally {
      setConfirming(false);
    }
  }

  return (
    <Sheet
      open={open}
      onClose={onClose}
      closeLabel={closeLabel}
      title={title}
      cornerAction={
        <FormIconSubmit
          type="button"
          variant="save"
          label={saveLabel}
          disabled={!croppedAreaPixels || confirming}
          onClick={() => void handleConfirm()}
        />
      }
      body={
        <div className="flex flex-col gap-(--space-3) h-full">
          <div className="relative w-full flex-1 min-h-[16rem]">
            <Cropper
              image={objectUrl}
              crop={crop}
              zoom={zoom}
              cropShape={cropShape}
              aspect={aspect}
              onCropChange={setCrop}
              onZoomChange={setZoom}
              onCropComplete={(_, areaPixels) =>
                setCroppedAreaPixels(areaPixels)
              }
            />
          </div>
          <input
            type="range"
            aria-label={zoomLabel}
            min={1}
            max={3}
            step={0.1}
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
            className="w-full"
          />
        </div>
      }
    />
  );
}

/**
 * Shared crop/zoom sheet: the avatar (SidePanelIdentity, AliasSetupForm) and, with a
 * rectangle and its own encoder, the recipe photo (RecipeImagePicker, S-067).
 */
export function AvatarCropSheet({
  file,
  open,
  onClose,
  ...editorProps
}: Props) {
  const objectUrl = useMemo(() => {
    if (!file) return null;
    return URL.createObjectURL(file);
  }, [file]);

  useEffect(() => {
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [objectUrl]);

  if (!file || !objectUrl) return null;

  return (
    <CropEditor
      key={objectUrl}
      file={file}
      objectUrl={objectUrl}
      open={open}
      onClose={onClose}
      {...editorProps}
    />
  );
}
