"""The shopping list export (spec 024): the Markdown copy and the PDF, built from one document.

Both formats read the same blocks, so they cannot drift apart (SC-002). Lines keep the order of
the saved list: measured cart lines, then items added by hand, then "Your call". Pure: no I/O,
no FastAPI, no SQLAlchemy; the PDF is built in memory with the standard library only (research R2).
"""

from __future__ import annotations

import textwrap
import zlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from domain.cart import COUNT_UNIT, Amount
from domain.shopping_list import SavedLine

Locale = Literal["en", "es"]
Block = tuple[Literal["heading", "item", "plain", "gap"], str]

LABELS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Shopping list",
        "your_call": "Your call",
        "manual": "(manual)",
        "empty": "No items",
    },
    "es": {
        "title": "Lista de compras",
        "your_call": "A tu criterio",
        "manual": "(manual)",
        "empty": "Sin artículos",
    },
}

# A4 in points, a 50 pt margin, one row per 16 pt, and rows wrapped to fit the text width.
PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN = 50
LEADING = 16
ROWS_PER_PAGE = (PAGE_HEIGHT - 2 * MARGIN) // LEADING
WRAP_WIDTH = 84
BODY_SIZE = 11
HEADING_SIZE = 14


@dataclass(frozen=True, slots=True)
class ExportLine:
    """One printed line: its text, its recipe titles, and whether it was added by hand."""

    text: str
    sources: tuple[str, ...]
    is_manual: bool


@dataclass(frozen=True, slots=True)
class ExportDocument:
    list_date: date
    lines: tuple[ExportLine, ...]
    your_call: tuple[ExportLine, ...]
    locale: Locale


def _amounts_text(amounts: Sequence[Amount]) -> str:
    """Amounts joined with " + "; a count shows its number only (as on screen, spec 023 FR-009)."""
    return " + ".join(
        amount.quantity if amount.unit == COUNT_UNIT else f"{amount.quantity} {amount.unit}"
        for amount in amounts
    )


def _measured_text(item: SavedLine) -> str:
    name = f"{item.name}, {item.size}" if item.size else item.name
    if not item.amounts:
        return name
    return f"{name} — {_amounts_text(item.amounts)}"


def _your_call_text(item: SavedLine) -> str:
    return f"{item.name} — {', '.join(item.notes)}"


def build_export_document(
    items: Sequence[SavedLine], list_date: date, locale: Locale
) -> ExportDocument:
    """The export of a saved list's items, in list order, in the viewer's words."""
    lines: list[ExportLine] = []
    your_call: list[ExportLine] = []
    for item in items:
        sources = tuple(ref.title for ref in item.recipes)
        if item.origin == "hand":
            lines.append(ExportLine(_measured_text(item), (), True))
        elif item.section == "your_call":
            your_call.append(ExportLine(_your_call_text(item), sources, False))
        else:
            lines.append(ExportLine(_measured_text(item), sources, False))
    return ExportDocument(list_date, tuple(lines), tuple(your_call), locale)


def _item_text(line: ExportLine, labels: dict[str, str]) -> str:
    if line.is_manual:
        return f"{line.text} {labels['manual']}"
    if line.sources:
        return f"{line.text} ({', '.join(line.sources)})"
    return line.text


def export_blocks(document: ExportDocument) -> list[Block]:
    """The printed structure, shared by the Markdown and the PDF."""
    labels = LABELS[document.locale]
    blocks: list[Block] = [
        ("heading", f"{labels['title']} ({document.list_date.isoformat()})"),
        ("gap", ""),
    ]
    if not document.lines and not document.your_call:
        blocks.append(("plain", labels["empty"]))
    blocks.extend(("item", _item_text(line, labels)) for line in document.lines)
    if document.your_call:
        if document.lines:
            blocks.append(("gap", ""))
        blocks.append(("heading", labels["your_call"]))
        blocks.append(("gap", ""))
        blocks.extend(("item", _item_text(line, labels)) for line in document.your_call)
    return blocks


def render_markdown(document: ExportDocument) -> str:
    """The Markdown copy (spec 024 FR-004, research R3)."""
    out: list[str] = []
    for kind, text in export_blocks(document):
        if kind == "heading":
            out.append(f"## {text}")
        elif kind == "item":
            out.append(f"- {text}")
        else:
            out.append(text)
    return "\n".join(out) + "\n"


def _escape(text: str) -> bytes:
    """WinAnsi bytes with the PDF string delimiters escaped; other characters become '?'."""
    raw = text.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _rows(document: ExportDocument) -> list[tuple[str, str]]:
    """Each printed row as (font, text), long text wrapped so no line runs off the page."""
    rows: list[tuple[str, str]] = []
    for kind, text in export_blocks(document):
        if kind == "gap":
            rows.append(("F1", ""))
            continue
        font = "F2" if kind == "heading" else "F1"
        for part in textwrap.wrap(text, WRAP_WIDTH, break_long_words=True) or [""]:
            rows.append((font, part))
    return rows


def _content(rows: Sequence[tuple[str, str]]) -> bytes:
    stream = bytearray()
    for index, (font, text) in enumerate(rows):
        size = HEADING_SIZE if font == "F2" else BODY_SIZE
        y = PAGE_HEIGHT - MARGIN - index * LEADING
        stream += b"BT /%s %d Tf %d %d Td (%s) Tj ET\n" % (
            font.encode(),
            size,
            MARGIN,
            y,
            _escape(text),
        )
    return bytes(stream)


def render_pdf(document: ExportDocument) -> bytes:
    """A PDF 1.4 file with base-14 Helvetica, one text stream per page and an xref table."""
    rows = _rows(document)
    pages = [rows[i : i + ROWS_PER_PAGE] for i in range(0, len(rows), ROWS_PER_PAGE)]

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # 2: the page tree, filled in once the pages are known
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]
    kids: list[int] = []
    for page_rows in pages:
        content = zlib.compress(_content(page_rows))
        objects.append(
            b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(content)
            + content
            + b"\nendstream"
        )
        content_id = len(objects)
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode()
        )
        kids.append(len(objects))
    kid_refs = " ".join(f"{kid} 0 R" for kid in kids)
    objects[1] = f"<< /Type /Pages /Kids [{kid_refs}] /Count {len(kids)} >>".encode()

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    out += b"startxref\n%d\n" % xref_at + b"%%EOF\n"
    return bytes(out)
