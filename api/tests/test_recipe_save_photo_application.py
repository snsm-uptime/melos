"""Save with a photo source (spec 041 T057): the source kind rules and the picture preview cap."""

from __future__ import annotations

import base64

import pytest
from domain.errors import InvalidPreviewImageError
from domain.recipe_draft import InvalidDraftError
from domain.recipe_preview import validate_picture_preview, validate_preview_image
from tests.test_recipe_save_application import Harness, personal

WEBP_HEADER = b"RIFF\x00\x00\x00\x00WEBP"
WEBP_URI = "data:image/webp;base64," + base64.b64encode(WEBP_HEADER).decode("ascii")
JPEG_URI = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 8).decode()


def _webp_of(size: int) -> str:
    data = WEBP_HEADER + b"\x00" * (size - len(WEBP_HEADER))
    return "data:image/webp;base64," + base64.b64encode(data).decode("ascii")


def _harness() -> tuple[Harness, object]:
    h = Harness()
    fact, nid = personal()
    h.add(fact)
    return h, nid


def test_a_photo_saves_with_the_photo_source_kind_and_no_text() -> None:
    h, nid = _harness()
    h.run(nid, source_text="", source_kind="photo", preview_image=WEBP_URI)
    recipe = h.recipes.stored[0]
    assert recipe.source_kind == "photo"
    assert recipe.source_text == ""
    assert recipe.source_url is None
    assert recipe.preview_image == WEBP_URI


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_kind": "photo", "source_text": "pasted"},
        {"source_kind": "photo", "source_text": "", "source_url": "https://example.test/x"},
        {"source_kind": "text", "source_text": "", "source_url": "https://example.test/x"},
        {"source_kind": "url", "source_text": "", "source_url": None},
    ],
    ids=["photo-with-text", "photo-with-url", "text-with-url", "url-with-no-url"],
)
def test_a_source_kind_that_disagrees_with_the_fields_is_refused(overrides: dict) -> None:
    h, nid = _harness()
    with pytest.raises(InvalidDraftError):
        h.run(nid, **overrides)
    assert h.recipes.stored == []


def test_no_kind_infers_a_link_when_a_url_is_sent_and_text_otherwise() -> None:
    h, nid = _harness()
    h.run(nid, source_text="", source_url="https://example.test/soup")
    h.run(nid)
    assert [r.source_kind for r in h.recipes.stored] == ["url", "text"]


def test_a_photo_with_no_preview_stores_none() -> None:
    h, nid = _harness()
    h.run(nid, source_text="", source_kind="photo")
    assert h.recipes.stored[0].preview_image is None


def test_the_picture_preview_accepts_webp_up_to_500_kb() -> None:
    assert validate_picture_preview(_webp_of(500_000))  # at the limit, passes
    with pytest.raises(InvalidPreviewImageError):
        validate_picture_preview(_webp_of(500_001))


def test_the_picture_preview_refuses_another_media_type() -> None:
    with pytest.raises(InvalidPreviewImageError):
        validate_picture_preview(JPEG_URI)


def test_the_link_preview_rule_is_unchanged() -> None:
    assert validate_preview_image(WEBP_URI) == WEBP_URI
    too_big = (
        "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff" + b"\x00" * 300_000).decode()
    )
    with pytest.raises(InvalidPreviewImageError):
        validate_preview_image(too_big)
