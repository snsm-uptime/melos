import { describe, expect, it } from "vitest";

import {
  DOWNSCALE_MAX_BYTES,
  downscalePicture,
  type DownscaleDeps,
  PictureDecodeError,
  type ScalingCanvas,
} from "./pictureDownscale";

type Recorded = { width: number; height: number; type: string; quality: number };

/**
 * A stub browser: the picture is `width` by `height`; the canvas encodes to a blob whose size
 * falls with quality, and supports WebP only when `webp` is true (else it returns a blob with
 * an empty type, as browsers without WebP do).
 */
function stubDeps(options: {
  width: number;
  height: number;
  webp?: boolean;
  bytesAt?: (quality: number) => number;
  failDecode?: boolean;
}): { deps: DownscaleDeps; encodes: Recorded[]; drawn: { width: number; height: number }[] } {
  const encodes: Recorded[] = [];
  const drawn: { width: number; height: number }[] = [];
  const bytesAt = options.bytesAt ?? (() => 100_000);
  const deps: DownscaleDeps = {
    async decode() {
      if (options.failDecode) throw new PictureDecodeError();
      return { width: options.width, height: options.height, source: {} };
    },
    createCanvas(width, height): ScalingCanvas {
      return {
        width,
        height,
        getContext: () => ({
          drawImage: (_image, _x, _y, w, h) => drawn.push({ width: w, height: h }),
        }),
        toBlob(callback, type = "image/png", quality = 1) {
          encodes.push({ width, height, type, quality });
          const supported = type === "image/jpeg" || options.webp !== false;
          const blobType = supported ? type : "";
          callback(new Blob([new Uint8Array(bytesAt(quality))], { type: blobType }));
        },
      };
    },
  };
  return { deps, encodes, drawn };
}

describe("downscalePicture", () => {
  it("keeps the longest side at 2,400 px or less and the aspect ratio", async () => {
    const { deps, drawn } = stubDeps({ width: 4000, height: 3000 });
    await downscalePicture(new File([new Uint8Array(4)], "a.jpg"), deps);
    expect(drawn[0]).toEqual({ width: 2400, height: 1800 });
  });

  it("leaves a small picture at its own size", async () => {
    const { deps, drawn } = stubDeps({ width: 800, height: 600 });
    await downscalePicture(new File([new Uint8Array(4)], "a.jpg"), deps);
    expect(drawn[0]).toEqual({ width: 800, height: 600 });
  });

  it("steps the quality down until the result is under 1.5 MB", async () => {
    const { deps, encodes } = stubDeps({
      width: 1000,
      height: 1000,
      bytesAt: (quality) => (quality > 0.75 ? 2_000_000 : 1_000_000),
    });
    const blob = await downscalePicture(new File([new Uint8Array(4)], "a.jpg"), deps);
    expect(blob.size).toBeLessThanOrEqual(DOWNSCALE_MAX_BYTES);
    expect(encodes.map((e) => e.quality)).toEqual([0.9, 0.9, 0.8, 0.7]);
  });

  it("encodes JPEG, the format the api accepts, even where the canvas could do WebP", async () => {
    const { deps, encodes } = stubDeps({ width: 100, height: 100, webp: true });
    const blob = await downscalePicture(new File([new Uint8Array(4)], "a.jpg"), deps);
    expect(blob.type).toBe("image/jpeg");
    expect(encodes.every((encode) => encode.type === "image/jpeg")).toBe(true);
  });

  it("never changes the chosen file", async () => {
    const chosen = new File([new Uint8Array([1, 2, 3])], "a.jpg", { type: "image/jpeg" });
    const { deps } = stubDeps({ width: 4000, height: 3000 });
    await downscalePicture(chosen, deps);
    expect(chosen.size).toBe(3);
    expect(chosen.name).toBe("a.jpg");
  });

  it("fails with a decode error when the browser cannot read the picture", async () => {
    const { deps } = stubDeps({ width: 0, height: 0, failDecode: true });
    await expect(downscalePicture(new File([new Uint8Array(4)], "a.heic"), deps)).rejects.toBeInstanceOf(
      PictureDecodeError,
    );
  });
});
