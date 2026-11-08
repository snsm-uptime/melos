"""Invented, tiny image byte strings for the picture tests (spec 041).

Each helper builds only the bytes a check looks at: a signature, a container
box, a filler. None of them is a real picture. `pil_image_bytes` (Pillow) lives
in the pipeline tests, so this module imports nothing outside the standard library.
"""

from __future__ import annotations

import struct

_JPEG_SIGNATURE = b"\xff\xd8\xff\xe0"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes) -> bytes:
    body = b"\x00" * 13 if kind == b"IHDR" else b""
    return struct.pack(">I", len(body)) + kind + body + b"\x00\x00\x00\x00"


def jpeg_bytes(*, eoi: bool = True, size: int = 2_000) -> bytes:
    """A JPEG signature, filler, and an end-of-image marker unless `eoi` is false."""
    tail = b"\xff\xd9" if eoi else b""
    filler = max(size - len(_JPEG_SIGNATURE) - len(tail), 0)
    return _JPEG_SIGNATURE + b"\x00" * filler + tail


def png_bytes(*, ihdr: bool = True, iend: bool = True) -> bytes:
    """A PNG signature with IHDR, IDAT and IEND chunks, each omitted by its flag."""
    data = _PNG_SIGNATURE
    if ihdr:
        data += _chunk(b"IHDR")
    data += _chunk(b"IDAT")
    if iend:
        data += _chunk(b"IEND")
    return data


def heic_bytes(brand: str = "heic", size: int = 64) -> bytes:
    """A 24-byte `ftyp` box whose major brand is `brand`, padded to `size`."""
    box = struct.pack(">I", 24) + b"ftyp" + brand.encode("ascii") + b"\x00" * 12
    return with_size(box, size)


def avif_bytes() -> bytes:
    """An `ftyp` box with the AVIF brand, which the picture rules refuse."""
    return heic_bytes(brand="avif")


def with_size(data: bytes, total: int) -> bytes:
    """Pad `data` with zero bytes to exactly `total` bytes (never truncates)."""
    if total <= len(data):
        return data
    return data + b"\x00" * (total - len(data))


def pil_image_bytes(
    format: str,
    size: tuple[int, int] = (64, 48),
    mode: str = "RGB",
    color: object = (200, 120, 60),
    orientation: int | None = None,
    noise: bool = False,
) -> bytes:
    """Encode a generated Pillow image.

    `orientation` writes an EXIF tag; `noise` replaces the pixels with seeded noise.
    """
    from io import BytesIO

    from PIL import Image

    image = Image.new(mode, size, color)
    if noise:
        import random

        rng = random.Random(7)
        image = Image.frombytes(
            mode,
            size,
            bytes(rng.randrange(256) for _ in range(size[0] * size[1] * len(mode))),
        )
    out = BytesIO()
    save_kwargs: dict[str, object] = {}
    if orientation is not None:
        exif = Image.Exif()
        exif[0x0112] = orientation
        save_kwargs["exif"] = exif.tobytes()
    if format.upper() == "JPEG" and mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image.save(out, format=format, **save_kwargs)
    return out.getvalue()
