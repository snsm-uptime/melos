"""Rules for recipe lists (spec 021) and for meaning search (spec 019).

Pure rules: no I/O, framework or database imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import ceil
from typing import Literal
from uuid import UUID

from domain.errors import (
    InvalidPageError,
    InvalidSearchFiltersError,
    InvalidSearchQuestionError,
)
from domain.ingredient_catalog import normalize_name

PAGE_SIZE = 12

# At most this many recipes per meaning search (spec 019 FR-017).
SEARCH_LIMIT = 5

Mark = Literal["close", "weak"]
SearchFeature = Literal["assistant", "list_search", "mcp", "test"]


def search_key(text: str) -> str:
    """The filter text as the lists compare it: no accents, case-folded, single spaces, trimmed."""
    return normalize_name(text)


def clamp_page(requested: int, total: int, page_size: int = PAGE_SIZE) -> tuple[int, int]:
    """(page, total_pages): a page past the last one becomes the last; below 1 is invalid."""
    if requested < 1:
        raise InvalidPageError()
    total_pages = max(1, ceil(total / page_size))
    return min(requested, total_pages), total_pages


# --- Meaning search (spec 019) ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Kitchen:
    """Every notebook of one kitchen."""

    kitchen_id: UUID
    kind: Literal["kitchen"] = "kitchen"


@dataclass(frozen=True, slots=True)
class MyNotebooks:
    """Every personal notebook the person owns or is a member of, worked out at search time."""

    kind: Literal["my_notebooks"] = "my_notebooks"


@dataclass(frozen=True, slots=True)
class OneNotebook:
    notebook_id: UUID
    kind: Literal["notebook"] = "notebook"


SearchScope = Kitchen | MyNotebooks | OneNotebook


@dataclass(frozen=True, slots=True)
class SearchFilters:
    """Narrow the recipes compared. Every filter given must hold (FR-015, FR-015a).

    Ingredient names are normalized and de-duplicated, in first-seen order.
    """

    author_id: UUID | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    ingredient_names: tuple[str, ...] = field(default=())
    exclude_recipe_ids: tuple[UUID, ...] = field(default=())

    def __post_init__(self) -> None:
        if (
            self.created_after is not None
            and self.created_before is not None
            and self.created_after > self.created_before
        ):
            raise InvalidSearchFiltersError()
        names: list[str] = []
        for name in self.ingredient_names:
            normalized = normalize_name(name)
            if normalized and normalized not in names:
                names.append(normalized)
        object.__setattr__(self, "ingredient_names", tuple(names))
        excluded = tuple(dict.fromkeys(self.exclude_recipe_ids))
        object.__setattr__(self, "exclude_recipe_ids", excluded)


def search_question(text: str) -> str:
    """The question as it is embedded: trimmed. Empty or blank is refused."""
    question = text.strip()
    if not question:
        raise InvalidSearchQuestionError()
    return question


def mark(score: float, minimum: float) -> Mark:
    """'close' at or above the configured minimum closeness, 'weak' below (FR-017)."""
    return "close" if score >= minimum else "weak"
