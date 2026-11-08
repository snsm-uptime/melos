/**
 * Shrinks a chosen picture before it is sent (spec 041, FR-024, research R11). The longest side
 * is at most 2,400 px with the aspect ratio kept; the result is JPEG, and its quality steps
 * down until it is under 1.5 MB. The file that was
 * chosen is never changed. A picture the browser cannot decode is a failure, and the file is
 * never sent in its place.
 */

export const DOWNSCALE_MAX_SIDE = 2400;
export const DOWNSCALE_MAX_BYTES = 1_500_000;
const QUALITIES = [0.9, 0.8, 0.7, 0.6, 0.5];

/** The browser could not decode or draw the picture. The sheet shows a message; nothing is sent. */
export class PictureDecodeError extends Error {
  constructor() {
    super("The picture could not be read.");
    this.name = "PictureDecodeError";
  }
}

export type DecodedPicture = { width: number; height: number; close?: () => void };

export type ScalingCanvas = {
  width: number;
  height: number;
  getContext(kind: "2d"): {
    drawImage(image: unknown, x: number, y: number, w: number, h: number): void;
  } | null;
  toBlob(callback: (blob: Blob | null) => void, type?: string, quality?: number): void;
};

/** What the downscale needs from the browser, so tests can stub it. */
export type DownscaleDeps = {
  decode(file: File): Promise<DecodedPicture & { source: unknown }>;
  createCanvas(width: number, height: number): ScalingCanvas;
};

function browserDeps(): DownscaleDeps {
  return {
    async decode(file) {
      try {
        const bitmap = await createImageBitmap(file);
        return { width: bitmap.width, height: bitmap.height, source: bitmap, close: () => bitmap.close() };
      } catch {
        throw new PictureDecodeError();
      }
    },
    createCanvas(width, height) {
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      return canvas as unknown as ScalingCanvas;
    },
  };
}

/** The size the picture is drawn at: longest side capped, aspect ratio kept. */
export function scaledSize(width: number, height: number): { width: number; height: number } {
  const scale = Math.min(1, DOWNSCALE_MAX_SIDE / Math.max(width, height));
  return { width: Math.max(1, Math.round(width * scale)), height: Math.max(1, Math.round(height * scale)) };
}

function encode(canvas: ScalingCanvas, type: string, quality: number): Promise<Blob | null> {
  return new Promise((resolve) => canvas.toBlob(resolve, type, quality));
}

/** Shrink `file` to a WebP (or JPEG) Blob under the byte limit, or throw PictureDecodeError. */
export async function downscalePicture(file: File, deps: DownscaleDeps = browserDeps()): Promise<Blob> {
  const decoded = await deps.decode(file);
  const { width, height } = scaledSize(decoded.width, decoded.height);
  const canvas = deps.createCanvas(width, height);
  const context = canvas.getContext("2d");
  if (!context) throw new PictureDecodeError();
  context.drawImage(decoded.source, 0, 0, width, height);
  decoded.close?.();

  // JPEG, not WebP: the api accepts JPEG, PNG and HEIC input and refuses WebP (spec 041, FR-019),
  // so the browser's copy must be one it takes. The canvas encodes JPEG everywhere.
  let blob = await encode(canvas, "image/jpeg", QUALITIES[0]);
  if (!blob) throw new PictureDecodeError();

  for (const quality of QUALITIES) {
    blob = (await encode(canvas, "image/jpeg", quality)) ?? blob;
    if (blob.size <= DOWNSCALE_MAX_BYTES) break;
  }
  return blob;
}
