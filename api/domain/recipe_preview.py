"""Recipe preview image rule: a data URI, checked for format and size (spec 026, research R9).

Pure, like `domain/photo.py`. The browser shrinks the photo before Save (800 px, JPEG); the
api only checks the prefix, the decoded size and that the bytes are the image the prefix says.
Constitution 2.0.0 principle 5: an image is stored only where a story says so, with a size
limit and a format check. S-067 (recipe image upload) reuses this rule.
"""

from __future__ import annotations

import base64
import binascii

from domain.errors import InvalidPreviewImageError

PREVIEW_MAX_DECODED_BYTES = 300_000
# Base64 expands payloads by ~4/3: refuse on the cheap length check before decoding.
PREVIEW_MAX_ENCODED_CHARS = (PREVIEW_MAX_DECODED_BYTES * 4 // 3) + 4
_PREFIXES = {
    "data:image/jpeg;base64,": "jpeg",
    "data:image/png;base64,": "png",
    "data:image/webp;base64,": "webp",
}


def _matches(kind: str, data: bytes) -> bool:
    if kind == "jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if kind == "png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def validate_preview_image(value: str | None) -> str | None:
    """Return the data URI unchanged, or raise InvalidPreviewImageError. None is no image."""
    if value is None:
        return None
    prefix = next((p for p in _PREFIXES if value.startswith(p)), None)
    if prefix is None:
        raise InvalidPreviewImageError("The image must be a JPEG, PNG or WebP data URI.")
    encoded = value[len(prefix) :]
    if not encoded:
        raise InvalidPreviewImageError("The image is empty.")
    if len(encoded) > PREVIEW_MAX_ENCODED_CHARS:
        raise InvalidPreviewImageError("The image is larger than 300 KB.")
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise InvalidPreviewImageError("The image must be valid base64.") from exc
    if len(decoded) > PREVIEW_MAX_DECODED_BYTES:
        raise InvalidPreviewImageError("The image is larger than 300 KB.")
    if not _matches(_PREFIXES[prefix], decoded):
        raise InvalidPreviewImageError("The image is not the format its prefix says.")
    return value
