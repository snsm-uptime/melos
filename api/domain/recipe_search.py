"""Rules for recipe lists: the filter key and the page window (spec 021).

Pure rules: no I/O, framework or database imports.
"""

from __future__ import annotations

from math import ceil

from domain.errors import InvalidPageError
from domain.ingredient_catalog import normalize_name

PAGE_SIZE = 12


def search_key(text: str) -> str:
    """The filter text as the lists compare it: no accents, case-folded, single spaces, trimmed."""
    return normalize_name(text)


def clamp_page(requested: int, total: int, page_size: int = PAGE_SIZE) -> tuple[int, int]:
    """(page, total_pages): a page past the last one becomes the last; below 1 is invalid."""
    if requested < 1:
        raise InvalidPageError()
    total_pages = max(1, ceil(total / page_size))
    return min(requested, total_pages), total_pages
