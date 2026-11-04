/**
 * Client-side avatar photo prep: canvas crop/resize to a 256x256 square and
 * base64-encode, capped near 200KB — done here so the backend never needs an
 * image library (no Pillow/sharp, no separate media storage).
 */

const AVATAR_SIZE = 256;
const TARGET_MAX_BYTES = 200_000;
const MIN_JPEG_QUALITY = 0.4;

export interface Area {
  x: number;
  y: number;
  width: number;
  height: number;
}

export function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not read image file."));
    };
    img.src = url;
  });
}

function drawCroppedSquare(img: HTMLImageElement, area: Area): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = AVATAR_SIZE;
  canvas.height = AVATAR_SIZE;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D context unavailable.");

  ctx.drawImage(img, area.x, area.y, area.width, area.height, 0, 0, AVATAR_SIZE, AVATAR_SIZE);
  return canvas;
}

function canvasToDataUri(canvas: HTMLCanvasElement, mimeType: string, quality?: number): string {
  return canvas.toDataURL(mimeType, quality);
}

function decodedByteLength(dataUri: string): number {
  const commaIndex = dataUri.indexOf(",");
  const base64 = commaIndex >= 0 ? dataUri.slice(commaIndex + 1) : dataUri;
  const padding = base64.endsWith("==") ? 2 : base64.endsWith("=") ? 1 : 0;
  return Math.floor((base64.length * 3) / 4) - padding;
}

/**
 * PNGs with transparency stay PNG (no quality knob to shrink with) as long
 * as they clear the size cap; everything else re-encodes as JPEG, stepping
 * quality down until it clears the size cap.
 */
function encodeCanvas(canvas: HTMLCanvasElement, mimeType: string): string {
  if (mimeType === "image/png") {
    const dataUri = canvasToDataUri(canvas, "image/png");
    if (decodedByteLength(dataUri) <= TARGET_MAX_BYTES) return dataUri;
    // Oversized PNG (e.g. a large transparent graphic) — fall through to
    // JPEG, which accepts a quality knob small pixel art rarely needs.
  }

  let quality = 0.9;
  let dataUri = canvasToDataUri(canvas, "image/jpeg", quality);
  while (decodedByteLength(dataUri) > TARGET_MAX_BYTES && quality > MIN_JPEG_QUALITY) {
    quality -= 0.1;
    dataUri = canvasToDataUri(canvas, "image/jpeg", quality);
  }
  return dataUri;
}

/**
 * Crop `img` to the caller-supplied source rectangle, resize to a 256x256
 * square, and encode as a base64 data URI, capped near 200KB.
 */
export async function encodeCroppedAvatar(
  img: HTMLImageElement,
  area: Area,
  mimeType: string,
): Promise<string> {
  const canvas = drawCroppedSquare(img, area);
  return encodeCanvas(canvas, mimeType);
}

// --- Recipe preview image (spec 026) ---

const PREVIEW_LONGEST_SIDE = 800;
export const PREVIEW_MAX_BYTES = 300_000;
const PREVIEW_QUALITIES = [0.85, 0.75, 0.65, 0.55, 0.45, 0.4];

function loadDataUri(dataUri: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Could not read image."));
    img.src = dataUri;
  });
}

/**
 * Shrink the page photo of a link capture before Save: longest side 800 px (never enlarged),
 * JPEG, quality stepped down from 0.85 to 0.4 until it fits 300 KB (the api's limit).
 * Returns null when the photo cannot be read or cannot fit; the recipe is then saved without it.
 */
export async function encodeRecipePreview(dataUri: string): Promise<string | null> {
  let img: HTMLImageElement;
  try {
    img = await loadDataUri(dataUri);
  } catch {
    return null;
  }
  const width = img.naturalWidth || img.width;
  const height = img.naturalHeight || img.height;
  if (!width || !height) return null;
  const scale = Math.min(1, PREVIEW_LONGEST_SIDE / Math.max(width, height));

  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(width * scale));
  canvas.height = Math.max(1, Math.round(height * scale));
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  // JPEG has no transparency: a white background instead of black.
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

  for (const quality of PREVIEW_QUALITIES) {
    const encoded = canvasToDataUri(canvas, "image/jpeg", quality);
    if (!encoded.startsWith("data:image/jpeg;base64,")) return null;
    if (decodedByteLength(encoded) <= PREVIEW_MAX_BYTES) return encoded;
  }
  return null;
}
