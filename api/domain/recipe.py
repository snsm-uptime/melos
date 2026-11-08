"""A recipe ready to be stored, and the rule that resolves its ingredient names (spec 020).

Pure: no I/O. The checked draft comes from `check_edited_draft`; this module only decides
which catalog spelling each line takes and which names are new.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal
from uuid import UUID

from domain.ingredient_catalog import CatalogLike, Language, as_index, same_spelling
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
    # Link capture (spec 026): the page address replaces the pasted text as the source.
    source_url: str | None = None
    # The recipe image, a data URI already checked by domain.recipe_preview.
    preview_image: str | None = None
    # The language most of the recipe is in (spec 043 FR-005a).
    language: Language = "es"
    # Where the recipe came from: "photo" stores a source row with no url and no text (spec 041).
    source_kind: Literal["text", "url", "photo"] = "text"


@dataclass(frozen=True, slots=True)
class EditedRecipe:
    """The content of a recipe after an edit (spec 027). Author, notebook and source stay."""

    title: str
    base_servings: int
    servings_estimated: bool
    lines: tuple[IngredientLine, ...]
    steps: tuple[str, ...]
    # The image (S-067): change_image False keeps the stored one; True stores preview_image,
    # where None removes it. preview_image is a data URI already checked by recipe_preview.
    change_image: bool = False
    preview_image: str | None = None
    # None keeps the stored language (spec 043). Setting one clears a pending proposal.
    language: Language | None = None
    # True drops the model's proposal without changing the language (FR-005a dismiss).
    dismiss_proposal: bool = False


def resolve_line_names(
    lines: Sequence[IngredientLine], catalog: CatalogLike
) -> tuple[tuple[IngredientLine, ...], tuple[str, ...]]:
    """Give each line the kept name of its catalog name, and list the names the catalog lacks.

    A name that differs from a catalog name (kept or other, spec 043) only by letter case or
    spacing takes that ingredient's kept name. Any other name is new and is listed once, in
    order of first appearance.
    """
    index = as_index(catalog)
    resolved: list[IngredientLine] = []
    new_names: list[str] = []
    for line in lines:
        entry = index.kept_for_spelling(line.name)
        if entry is not None:
            resolved.append(replace(line, name=entry))
            continue
        new = next((n for n in new_names if same_spelling(n, line.name)), None)
        if new is None:
            new_names.append(line.name)
            new = line.name
        resolved.append(replace(line, name=new))
    return tuple(resolved), tuple(new_names)
