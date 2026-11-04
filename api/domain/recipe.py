"""A recipe ready to be stored, and the rule that resolves its ingredient names (spec 020).

Pure: no I/O. The checked draft comes from `check_edited_draft`; this module only decides
which catalog spelling each line takes and which names are new.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from domain.ingredient_catalog import same_spelling
from domain.recipe_draft import IngredientLine

# Largest draft Save accepts (spec FR-019).
MAX_LINES = 100
MAX_STEPS = 100


@dataclass(frozen=True, slots=True)
class NewRecipe:
    title: str
    base_servings: int
    servings_estimated: bool
    lines: tuple[IngredientLine, ...]
    steps: tuple[str, ...]
    source_text: str
    author_id: UUID
    notebook_id: UUID
    save_key: UUID | None = None


@dataclass(frozen=True, slots=True)
class EditedRecipe:
    """The content of a recipe after an edit (spec 027). Author, notebook and source stay."""

    title: str
    base_servings: int
    servings_estimated: bool
    lines: tuple[IngredientLine, ...]
    steps: tuple[str, ...]


def resolve_line_names(
    lines: Sequence[IngredientLine], catalog_names: Iterable[str]
) -> tuple[tuple[IngredientLine, ...], tuple[str, ...]]:
    """Give each line the catalog spelling of its name, and list the names the catalog lacks.

    A name that differs from an entry only by letter case or spacing takes the entry's
    spelling. Any other name is new and is listed once, in order of first appearance.
    """
    entries = [name for name in catalog_names if name]
    resolved: list[IngredientLine] = []
    new_names: list[str] = []
    for line in lines:
        entry = next((e for e in entries if same_spelling(e, line.name)), None)
        if entry is not None:
            resolved.append(replace(line, name=entry))
            continue
        new = next((n for n in new_names if same_spelling(n, line.name)), None)
        if new is None:
            new_names.append(line.name)
            new = line.name
        resolved.append(replace(line, name=new))
    return tuple(resolved), tuple(new_names)
