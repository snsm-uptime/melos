"""The PDF writer (spec 024 FR-005, FR-006, research R2), checked without a PDF library."""

from __future__ import annotations

import re
import zlib
from datetime import date
from uuid import uuid4

from domain.cart import Amount, RecipeRef
from domain.shopping_export import ExportDocument, ExportLine, build_export_document, render_pdf
from domain.shopping_list import SavedLine

DAY = date(2026, 11, 17)
A = RecipeRef(uuid4(), "Recipe A")


def document(*lines: ExportLine) -> ExportDocument:
    return ExportDocument(DAY, lines, (), "en")


def streams(pdf: bytes) -> str:
    """The decompressed page content, joined."""
    parts = re.findall(rb"stream\n(.*?)\nendstream", pdf, re.S)
    return "\n".join(zlib.decompress(part).decode("cp1252") for part in parts)


def test_output_is_a_pdf_1_4_file() -> None:
    pdf = render_pdf(document(ExportLine("flour — 1 cup", ("Recipe A",), False)))
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf.rstrip().endswith(b"%%EOF")


def test_the_recipe_titles_are_printed_after_the_line_in_parentheses() -> None:
    items = (
        SavedLine("cart", "measured", "flour", "volume", None, (Amount("1", "cup"),), (), (A,)),
    )
    pdf = render_pdf(build_export_document(items, DAY, "en"))
    assert "flour — 1 cup \\(Recipe A\\)" in streams(pdf)


def test_a_hundred_lines_span_more_than_one_page() -> None:
    lines = tuple(ExportLine(f"item {i}", (), False) for i in range(100))
    pdf = render_pdf(document(*lines))
    assert pdf.count(b"/Type /Page ") >= 2
    assert all(f"(item {i}) Tj".encode() in zlib_all(pdf) for i in range(100))


def zlib_all(pdf: bytes) -> bytes:
    return streams(pdf).encode("cp1252")


def test_accents_are_written_in_winansi() -> None:
    pdf = render_pdf(document(ExportLine("azúcar y ñandú ¿qué?", (), False)))
    assert "azúcar y ñandú ¿qué?".encode("cp1252") in zlib_all(pdf)


def test_a_character_outside_winansi_becomes_a_question_mark() -> None:
    pdf = render_pdf(document(ExportLine("ελιά", (), False)))
    assert b"(????)" in zlib_all(pdf)


def test_parentheses_and_backslashes_are_escaped_in_the_content() -> None:
    pdf = render_pdf(document(ExportLine("a (b) \\ c", (), False)))
    assert rb"(a \(b\) \\ c)" in zlib_all(pdf)
