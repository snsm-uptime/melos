import { describe, expect, it } from "vitest";

import { checkPicture, MAX_PICTURE_BYTES } from "./pictureRules";

/** Invented bytes, built like `api/tests/picture_bytes.py` (signatures and boxes only). */
function jpeg(size = 2_000): Uint8Array {
  const bytes = new Uint8Array(size);
  bytes.set([0xff, 0xd8, 0xff, 0xe0]);
  return bytes;
}

function chunk(kind: string): number[] {
  const body = kind === "IHDR" ? new Array<number>(13).fill(0) : [];
  return [0, 0, 0, body.length, ...Array.from(kind, (c) => c.charCodeAt(0)), ...body, 0, 0, 0, 0];
}

function png({ ihdr = true, iend = true } = {}): Uint8Array {
  const parts = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
  if (ihdr) parts.push(...chunk("IHDR"));
  parts.push(...chunk("IDAT"));
  if (iend) parts.push(...chunk("IEND"));
  return Uint8Array.from(parts);
}

function heic(brand = "heic", size = 64): Uint8Array {
  const bytes = new Uint8Array(size);
  bytes.set([0, 0, 0, 24, ...Array.from("ftyp", (c) => c.charCodeAt(0))], 0);
  bytes.set(Array.from(brand, (c) => c.charCodeAt(0)), 8);
  return bytes;
}

function file(bytes: Uint8Array, name = "picture.bin", type = ""): File {
  return new File([new Uint8Array(bytes)], name, { type });
}

describe("checkPicture", () => {
  it.each([
    ["jpeg", jpeg(), "image/jpeg"],
    ["png", png(), "image/png"],
    ["heic", heic("heic"), "image/heic"],
    ["heix", heic("heix"), "image/heic"],
    ["hevc", heic("hevc"), "image/heic"],
    ["mif1", heic("mif1"), "image/heif"],
    ["msf1", heic("msf1"), "image/heif"],
  ])("accepts %s", async (_, bytes, mediaType) => {
    expect(await checkPicture(file(bytes))).toEqual({ ok: true, mediaType });
  });

  it("accepts a JPEG with no end marker (signature only)", async () => {
    const bytes = jpeg(2_000);
    expect(await checkPicture(file(bytes))).toEqual({ ok: true, mediaType: "image/jpeg" });
  });

  it("refuses a file over the size limit before reading it", async () => {
    const big = { size: MAX_PICTURE_BYTES + 1 } as File;
    expect(await checkPicture(big)).toEqual({ ok: false, reason: "too_large" });
  });

  it("accepts a file exactly at the limit", async () => {
    const edge = {
      size: MAX_PICTURE_BYTES,
      slice: () => new Blob([new Uint8Array(jpeg(4))]),
    } as unknown as File;
    expect(await checkPicture(edge)).toEqual({ ok: true, mediaType: "image/jpeg" });
  });

  it.each([
    ["a PDF", new TextEncoder().encode("%PDF-1.7\n")],
    ["plain text", new TextEncoder().encode("hello, not a picture")],
    ["a GIF", new TextEncoder().encode("GIF89a\0\0\0\0\0\0")],
    ["a WebP", new TextEncoder().encode("RIFF\0\0\0\0WEBPVP8 ")],
    ["an AVIF", heic("avif")],
    ["a PNG with no IEND", png({ iend: false })],
    ["a PNG with no IHDR", png({ ihdr: false })],
    ["a HEIC shorter than its box", heic("heic").slice(0, 10)],
    ["an empty file", new Uint8Array(0)],
  ])("refuses %s", async (_, bytes) => {
    expect(await checkPicture(file(bytes))).toEqual({ ok: false, reason: "unsupported" });
  });

  it("never uses the file name or the announced type", async () => {
    const pdf = file(new TextEncoder().encode("%PDF-1.7\n"), "a.jpg", "image/jpeg");
    expect(await checkPicture(pdf)).toEqual({ ok: false, reason: "unsupported" });
  });
});
