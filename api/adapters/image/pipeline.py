"""Picture pipeline (spec 041, FR-026): decode, orient, measure, choose a tier, compress to WebP.

Steps: open → exif orientation → RGB (alpha flattened on white) → Laplacian (printed pictures
only, FR-025) → tier → the encoding ladder; the first step within the tier's cap wins.
The original bytes are never returned. Logs carry tier, sharpness, dimensions, size and steps
only, never the bytes or base64 (FR-021).
"""

from __future__ import annotations

import logging
from io import BytesIO

import numpy as np
import pillow_heif
from application.ports import ProcessedPicture
from domain.picture_tiers import (
    CalibrationTable,
    EncodingStep,
    cap_bytes,
    choose_tier,
    plan_encoding,
)
from domain.recipe_picture import CheckedPicture, PictureRefused
from PIL import Image, ImageOps, UnidentifiedImageError

from adapters.image.laplacian import laplacian_sharpness

logger = logging.getLogger(__name__)

MAX_PIXELS = 64_000_000
# Pillow's own bomb error sits above our explicit limit, so ours is the one that fires.
Image.MAX_IMAGE_PIXELS = 128_000_000
# The largest side any tier asks for; JPEG draft decoding may only reduce to this size.
_LARGEST_SIDE = 2400

pillow_heif.register_heif_opener()


class PillowPicturePipeline:
    """Implements the PicturePipeline port with Pillow and pillow-heif."""

    def process(
        self,
        picture: CheckedPicture,
        *,
        handwritten: bool,
        table: CalibrationTable,
    ) -> ProcessedPicture:
        image, original = _decode(picture)
        sharpness: float | None = None
        if not handwritten:
            gray = np.asarray(image.convert("L"), dtype=np.float32)
            sharpness = laplacian_sharpness(gray)
        tier = choose_tier(handwritten, sharpness, table)
        cap = cap_bytes(tier)

        taken: list[EncodingStep] = []
        for step in plan_encoding(tier):
            taken.append(step)
            candidate = image.copy()
            candidate.thumbnail((step.max_side, step.max_side), Image.Resampling.LANCZOS)
            out = BytesIO()
            candidate.save(out, format="WEBP", quality=step.quality, method=6)
            webp = out.getvalue()
            if len(webp) <= cap:
                result = ProcessedPicture(
                    webp=webp,
                    tier=tier,
                    sharpness=sharpness,
                    original_dimensions=original,
                    final_dimensions=candidate.size,
                    size_kb=round(len(webp) / 1000, 1),
                    steps_taken=tuple(taken),
                )
                logger.info(
                    "picture processed tier=%s sharpness=%s original=%s final=%s "
                    "size_kb=%s steps=%s",
                    tier.value,
                    None if sharpness is None else round(sharpness, 2),
                    original,
                    result.final_dimensions,
                    result.size_kb,
                    len(taken),
                )
                return result

        logger.info("picture over cap tier=%s steps=%s", tier.value, len(taken))
        raise PictureRefused("too_large")


def _decode(picture: CheckedPicture) -> tuple[Image.Image, tuple[int, int]]:
    """Open, check the pixel count before decoding, orient, and flatten to RGB."""
    try:
        image = Image.open(BytesIO(picture.data))
        width, height = image.size
        if width * height > MAX_PIXELS:
            raise PictureRefused("unsupported")
        if picture.media_type == "image/jpeg":
            image.draft("RGB", (_LARGEST_SIDE, _LARGEST_SIDE))
        oriented = ImageOps.exif_transpose(image)
        original = (width, height)
        return _to_rgb(oriented), original
    except PictureRefused:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as error:
        raise PictureRefused("unsupported") from error


def _to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        flat = Image.new("RGB", rgba.size, (255, 255, 255))
        flat.paste(rgba, mask=rgba.split()[3])
        return flat
    return image.convert("RGB")
