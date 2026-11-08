/**
 * The picture check the sheet runs before anything is sent (spec 041, FR-019 to FR-021). It
 * mirrors `api/domain/recipe_picture.py`: size from `file.size` first, then the signature and
 * the container structure. The file's name and its `type` are never used. Only the bytes the
 * check needs are read.
 */

/** The largest accepted file, in bytes (10 MB, decimal, as the api counts it). */
export const MAX_PICTURE_BYTES = 10_000_000;

export type PictureCheck =
  | { ok: true; mediaType: "image/jpeg" | "image/png" | "image/heic" | "image/heif" }
  | { ok: false; reason: "unsupported" | "too_large" };

const HEIC_BRANDS = ["heic", "heix", "heim", "heis", "hevc", "hevx"];
const HEIF_BRANDS = ["mif1", "msf1"];
const FTYP_BOX_SIZE = 24;
const PNG_SIGNATURE = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];

async function bytesOf(file: Blob, start: number, end: number): Promise<Uint8Array> {
  return new Uint8Array(await file.slice(start, end).arrayBuffer());
}

function ascii(bytes: Uint8Array, start: number, end: number): string {
  return String.fromCharCode(...bytes.slice(start, end));
}

function startsWith(bytes: Uint8Array, prefix: number[]): boolean {
  return prefix.every((value, index) => bytes[index] === value);
}

/** Check one chosen or dropped file. Never reads the whole file. */
export async function checkPicture(file: File): Promise<PictureCheck> {
  if (file.size === 0) return { ok: false, reason: "unsupported" };
  if (file.size > MAX_PICTURE_BYTES) return { ok: false, reason: "too_large" };

  const head = await bytesOf(file, 0, Math.min(FTYP_BOX_SIZE, file.size));

  if (startsWith(head, [0xff, 0xd8, 0xff])) return { ok: true, mediaType: "image/jpeg" };

  if (startsWith(head, PNG_SIGNATURE)) {
    // The first chunk is IHDR (bytes 12 to 16) and the file ends with an IEND chunk type.
    const firstChunk = ascii(head, 12, 16);
    const tail = await bytesOf(file, file.size - 8, file.size);
    const lastChunk = ascii(tail, 0, 4);
    return firstChunk === "IHDR" && lastChunk === "IEND"
      ? { ok: true, mediaType: "image/png" }
      : { ok: false, reason: "unsupported" };
  }

  if (head.length >= FTYP_BOX_SIZE && ascii(head, 4, 8) === "ftyp") {
    const brand = ascii(head, 8, 12);
    if (HEIC_BRANDS.includes(brand)) return { ok: true, mediaType: "image/heic" };
    if (HEIF_BRANDS.includes(brand)) return { ok: true, mediaType: "image/heif" };
  }

  return { ok: false, reason: "unsupported" };
}
