"""The recipe preview image rule (spec 026 T033, research R9)."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from domain.errors import InvalidPreviewImageError
from domain.recipe_preview import PREVIEW_MAX_DECODED_BYTES, validate_preview_image

PAGES = Path(__file__).parent / "fixtures" / "pages"


def _uri(media_type: str, data: bytes) -> str:
    return f"data:{media_type};base64,{base64.b64encode(data).decode()}"


@pytest.mark.parametrize(
    ("name", "media_type"),
    [("photo.jpg", "image/jpeg"), ("photo.png", "image/png"), ("photo.webp", "image/webp")],
)
def test_accepts_jpeg_png_and_webp(name: str, media_type: str) -> None:
    value = _uri(media_type, (PAGES / name).read_bytes())

    assert validate_preview_image(value) == value


def test_none_means_no_image() -> None:
    assert validate_preview_image(None) is None


def test_accepts_exactly_the_limit() -> None:
    data = b"\xff\xd8\xff" + b"\0" * (PREVIEW_MAX_DECODED_BYTES - 3)

    assert PREVIEW_MAX_DECODED_BYTES == 300_000
    assert validate_preview_image(_uri("image/jpeg", data))


@pytest.mark.parametrize(
    "value",
    [
        "data:image/gif;base64,R0lGODlhAQABAAAAACw=",
        "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=",
        "https://example.test/a.jpg",
        "data:image/jpeg,raw",
        "",
    ],
)
def test_refuses_other_prefixes(value: str) -> None:
    with pytest.raises(InvalidPreviewImageError):
        validate_preview_image(value)


def test_refuses_an_empty_payload_and_invalid_base64() -> None:
    for value in ("data:image/jpeg;base64,", "data:image/png;base64,not*base64!"):
        with pytest.raises(InvalidPreviewImageError):
            validate_preview_image(value)


def test_refuses_over_the_limit() -> None:
    data = b"\xff\xd8\xff" + b"\0" * (PREVIEW_MAX_DECODED_BYTES - 2)

    with pytest.raises(InvalidPreviewImageError):
        validate_preview_image(_uri("image/jpeg", data))


def test_refuses_a_huge_string_before_decoding() -> None:
    value = "data:image/jpeg;base64," + "A" * (PREVIEW_MAX_DECODED_BYTES * 2)

    with pytest.raises(InvalidPreviewImageError, match="300"):
        validate_preview_image(value)


@pytest.mark.parametrize(
    ("media_type", "name"),
    [("image/png", "photo.jpg"), ("image/jpeg", "photo.webp"), ("image/webp", "photo.png")],
)
def test_refuses_bytes_that_do_not_match_the_prefix(media_type: str, name: str) -> None:
    with pytest.raises(InvalidPreviewImageError):
        validate_preview_image(_uri(media_type, (PAGES / name).read_bytes()))


def test_refuses_bytes_that_are_no_image() -> None:
    with pytest.raises(InvalidPreviewImageError):
        validate_preview_image(_uri("image/jpeg", (PAGES / "not_image.bin").read_bytes()))
