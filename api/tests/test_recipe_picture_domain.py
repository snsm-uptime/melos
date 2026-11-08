"""Image rules for picture capture (spec 041, FR-019 to FR-021, plan I3)."""

from __future__ import annotations

import base64

import pytest
from domain.recipe_picture import (
    PICTURE_MAX_BYTES,
    PICTURE_MAX_ENCODED_CHARS,
    CheckedPicture,
    PictureRefused,
    check_picture,
)
from tests.picture_bytes import (
    avif_bytes,
    heic_bytes,
    jpeg_bytes,
    png_bytes,
    with_size,
)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _refused_kind(image_base64: str) -> str:
    with pytest.raises(PictureRefused) as caught:
        check_picture(image_base64)
    return caught.value.kind


def test_accepts_each_supported_signature() -> None:
    assert check_picture(_b64(jpeg_bytes())) == CheckedPicture(jpeg_bytes(), "image/jpeg")
    assert check_picture(_b64(png_bytes())) == CheckedPicture(png_bytes(), "image/png")


@pytest.mark.parametrize("brand", ["heic", "heix", "heim", "heis", "hevc", "hevx"])
def test_heic_brands_are_heic(brand: str) -> None:
    assert check_picture(_b64(heic_bytes(brand))).media_type == "image/heic"


@pytest.mark.parametrize("brand", ["mif1", "msf1"])
def test_heif_brands_are_heif(brand: str) -> None:
    assert check_picture(_b64(heic_bytes(brand))).media_type == "image/heif"


def test_jpeg_without_end_marker_passes_on_signature_alone() -> None:
    assert check_picture(_b64(jpeg_bytes(eoi=False))).media_type == "image/jpeg"


def test_empty_string_is_empty() -> None:
    assert _refused_kind("") == "empty"


def test_encoded_length_is_checked_before_decoding() -> None:
    # Not valid base64, and too long: must be refused as too_large without decoding.
    assert _refused_kind("!" * (PICTURE_MAX_ENCODED_CHARS + 1)) == "too_large"


def test_decoded_size_limit_is_inclusive() -> None:
    at_limit = with_size(jpeg_bytes(), PICTURE_MAX_BYTES)
    assert len(check_picture(_b64(at_limit)).data) == PICTURE_MAX_BYTES
    over = with_size(jpeg_bytes(), PICTURE_MAX_BYTES + 1)
    assert _refused_kind(_b64(over)) == "too_large"


@pytest.mark.parametrize(
    "data",
    [
        b"plain text, not a picture",
        b"%PDF-1.7\n" + b"\x00" * 64,
        b"GIF89a" + b"\x00" * 64,
        b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 64,
        avif_bytes(),
        png_bytes(iend=False),
        png_bytes(ihdr=False),
        heic_bytes()[:10],
    ],
    ids=["text", "pdf", "gif", "webp", "avif", "png-no-iend", "png-no-ihdr", "heic-short"],
)
def test_unsupported_content_is_refused(data: bytes) -> None:
    assert _refused_kind(_b64(data)) == "unsupported"


def test_invalid_base64_is_unsupported() -> None:
    assert _refused_kind("not base64 !!!") == "unsupported"
