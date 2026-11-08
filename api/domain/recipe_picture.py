"""Image rules for picture capture (spec 041, FR-019 to FR-021, plan I3).

Pure: a base64 string in, a checked picture out. The check reads the bytes' signature
and container structure only, never the file name or a client-announced type, and it
never decodes an image. Stdlib only.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import Literal

from domain.errors import DomainError

PICTURE_MAX_BYTES = 10_000_000
PICTURE_MAX_ENCODED_CHARS = 13_333_336  # ceil(10_000_000 / 3) * 4

_JPEG_SIGNATURE = b"\xff\xd8\xff"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_HEIC_BRANDS = frozenset({b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevx"})
_HEIF_BRANDS = frozenset({b"mif1", b"msf1"})
_FTYP_BOX_SIZE = 24

MediaType = Literal["image/jpeg", "image/png", "image/heic", "image/heif"]
RefusalKind = Literal["empty", "unsupported", "too_large"]


@dataclass(frozen=True, slots=True)
class CheckedPicture:
    """Decoded bytes of a picture that passed the signature and structure checks."""

    data: bytes
    media_type: MediaType


class PictureRefused(DomainError):
    """The picture cannot be used. `kind` says why, for the route's code."""

    def __init__(self, kind: RefusalKind) -> None:
        super().__init__(kind)
        self.kind = kind


def check_picture(image_base64: str) -> CheckedPicture:
    """Check a standard base64 picture; raise `PictureRefused` when it cannot be used.

    Order: empty, encoded length, decode, decoded size, signature, structure.
    """
    if not image_base64:
        raise PictureRefused("empty")
    if len(image_base64) > PICTURE_MAX_ENCODED_CHARS:
        raise PictureRefused("too_large")
    try:
        data = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise PictureRefused("unsupported") from error
    if len(data) > PICTURE_MAX_BYTES:
        raise PictureRefused("too_large")
    return CheckedPicture(data, _media_type(data))


def _media_type(data: bytes) -> MediaType:
    if data.startswith(_JPEG_SIGNATURE):
        return "image/jpeg"
    if data.startswith(_PNG_SIGNATURE):
        if _has_png_chunks(data):
            return "image/png"
        raise PictureRefused("unsupported")
    if len(data) >= _FTYP_BOX_SIZE and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in _HEIC_BRANDS:
            return "image/heic"
        if brand in _HEIF_BRANDS:
            return "image/heif"
    raise PictureRefused("unsupported")


def _has_png_chunks(data: bytes) -> bool:
    """The first chunk is IHDR and the file ends with an IEND chunk (length, type, CRC)."""
    first_chunk = data[len(_PNG_SIGNATURE) + 4 : len(_PNG_SIGNATURE) + 8]
    last_chunk = data[-8:-4]
    return first_chunk == b"IHDR" and last_chunk == b"IEND"
