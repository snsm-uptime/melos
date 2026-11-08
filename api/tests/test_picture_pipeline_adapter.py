"""The picture pipeline on generated images (spec 041, FR-025, FR-026, FR-021)."""

from __future__ import annotations

import base64
import logging
from datetime import date
from io import BytesIO

import pytest
from adapters.image import pipeline as pipeline_module
from adapters.image.pipeline import PillowPicturePipeline
from domain.picture_tiers import CalibrationTable, Tier, cap_bytes
from domain.recipe_picture import CheckedPicture, PictureRefused
from PIL import Image
from tests.picture_bytes import jpeg_bytes, pil_image_bytes, png_bytes

TABLE = CalibrationTable(
    low=100.0,
    high=500.0,
    labelled_set="test",
    calibrated_on=date(2026, 11, 7),
    status="calibrated",
)


def _checked(data: bytes, media_type: str) -> CheckedPicture:
    return CheckedPicture(data=data, media_type=media_type)  # type: ignore[arg-type]


def _run(data: bytes, media_type: str = "image/png", *, handwritten: bool = True):  # noqa: ANN202
    return PillowPicturePipeline().process(
        _checked(data, media_type), handwritten=handwritten, table=TABLE
    )


def _size_of(webp: bytes) -> tuple[int, int]:
    return Image.open(BytesIO(webp)).size


def test_palette_png_and_rgba_png_come_out_as_rgb_webp() -> None:
    palette = pil_image_bytes("PNG", mode="P")
    rgba = pil_image_bytes("PNG", mode="RGBA", color=(10, 20, 30, 128))
    for data in (palette, rgba):
        result = _run(data)
        assert result.webp[:4] == b"RIFF" and result.webp[8:12] == b"WEBP"
        assert Image.open(BytesIO(result.webp)).mode in ("RGB", "RGBA")


def test_exif_orientation_six_swaps_width_and_height() -> None:
    data = pil_image_bytes("JPEG", size=(80, 40), orientation=6)
    result = _run(data, "image/jpeg")
    assert result.original_dimensions == (80, 40)  # as stored, before orientation
    assert result.final_dimensions == (40, 80)  # after the orientation is applied
    assert _size_of(result.webp) == (40, 80)


def test_an_invented_heic_decodes_and_comes_out_as_webp() -> None:
    pillow_heif = pytest.importorskip("pillow_heif")
    heif = pillow_heif.from_pillow(Image.new("RGB", (60, 40), (90, 90, 90)))
    buffer = BytesIO()
    heif.save(buffer, format="HEIF")
    result = _run(buffer.getvalue(), "image/heic")
    assert result.webp[8:12] == b"WEBP"


def test_handwritten_skips_the_laplacian_and_uses_tier_3(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_: object) -> float:
        raise AssertionError("the Laplacian must not run for handwriting")

    monkeypatch.setattr(pipeline_module, "laplacian_sharpness", fail)
    result = _run(pil_image_bytes("PNG"), handwritten=True)
    assert result.sharpness is None
    assert result.tier is Tier.TIER_3


def test_printed_measures_and_follows_the_thresholds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[float] = []

    def fake_sharpness(gray: object) -> float:
        return calls.pop(0)

    monkeypatch.setattr(pipeline_module, "laplacian_sharpness", fake_sharpness)
    data = pil_image_bytes("PNG")
    for measured, tier in ((10.0, Tier.TIER_3), (300.0, Tier.TIER_2), (900.0, Tier.TIER_1)):
        calls.append(measured)
        result = _run(data, handwritten=False)
        assert result.sharpness == measured
        assert result.tier is tier


def test_a_flat_picture_over_the_pixel_limit_is_refused_before_decoding() -> None:
    data = pil_image_bytes("PNG", size=(8_100, 8_100))
    with pytest.raises(PictureRefused) as caught:
        _run(data)
    assert caught.value.kind == "unsupported"


def test_a_noisy_picture_is_compressed_under_the_cap() -> None:
    noisy = pil_image_bytes("PNG", size=(700, 500), noise=True)
    result = _run(noisy, handwritten=True)
    assert len(result.webp) <= cap_bytes(result.tier)
    assert len(result.steps_taken) >= 1


def test_still_over_cap_at_the_floor_is_refused_as_too_large(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline_module, "cap_bytes", lambda tier: 1)
    with pytest.raises(PictureRefused) as caught:
        _run(pil_image_bytes("PNG", size=(200, 150), noise=True))
    assert caught.value.kind == "too_large"


def test_output_is_webp_and_never_the_original() -> None:
    data = pil_image_bytes("PNG")
    result = _run(data)
    assert result.webp != data
    assert result.webp[:4] == b"RIFF"
    assert result.size_kb == round(len(result.webp) / 1000, 1)


def test_logs_carry_metadata_and_never_the_bytes(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Alembic's fileConfig (run by the Postgres tests) can disable existing loggers.
    monkeypatch.setattr(pipeline_module.logger, "disabled", False)
    caplog.set_level(logging.INFO)
    data = pil_image_bytes("PNG")
    marker = base64.b64encode(data).decode("ascii")[:24]
    _run(data)
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "tier=tier_3" in text
    assert marker not in text
    assert "RIFF" not in text


def test_a_truncated_picture_is_unsupported() -> None:
    with pytest.raises(PictureRefused) as caught:
        _run(png_bytes()[:40])
    assert caught.value.kind == "unsupported"


def test_jpeg_without_end_marker_is_unsupported_when_it_cannot_decode() -> None:
    with pytest.raises(PictureRefused):
        _run(jpeg_bytes(eoi=False), "image/jpeg")
