/**
 * Crops a chosen picture to the rectangle the member framed (spec 041, the profile picture's
 * crop logic). The result is a new JPEG file, which then goes through the usual check and send.
 * The original file is not changed.
 */

import { type Area, loadImage } from "@/lib/imageEncode";

const CROP_QUALITY = 0.92;

export async function cropPictureFile(file: File, area: Area): Promise<File> {
  const img = await loadImage(file);
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(area.width));
  canvas.height = Math.max(1, Math.round(area.height));
  const context = canvas.getContext("2d");
  if (!context) throw new Error("the browser cannot draw the picture");
  context.drawImage(img, area.x, area.y, area.width, area.height, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise<Blob>((resolve, reject) =>
    canvas.toBlob(
      (out) => (out ? resolve(out) : reject(new Error("the picture could not be encoded"))),
      "image/jpeg",
      CROP_QUALITY,
    ),
  );
  return new File([blob], "cropped.jpg", { type: "image/jpeg" });
}
