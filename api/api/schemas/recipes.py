"""Request and response bodies for recipes (spec 020 save, spec 027 detail, edit, delete)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from domain.recipe import MAX_LINES, MAX_STEPS
from pydantic import BaseModel, Field


class SaveIngredientLine(BaseModel):
    name: str
    vague: bool = False
    quantity: float | None = None
    unit: str | None = None
    size: str | None = None
    preparation: str | None = None
    note: str | None = None


class SaveRecipeBody(BaseModel):
    save_key: UUID
    notebook_id: UUID | None = None
    kitchen_id: UUID | None = None
    source_text: str = ""
    title: str
    base_servings: int
    servings_estimated: bool = False
    # The same limits as the use case (spec FR-019); the use case also checks them.
    ingredient_lines: list[SaveIngredientLine] = Field(max_length=MAX_LINES + 1)
    steps: list[str] = Field(max_length=MAX_STEPS + 1)


class UpdateRecipeBody(BaseModel):
    """Replace a recipe's content (spec 027, contracts/recipe-api.md).

    The ingredient line model is the save route's, so the two screens share one shape.
    """

    # The `version` read with the recipe; the edit is refused if the recipe changed since.
    version: datetime
    title: str
    base_servings: int
    servings_estimated: bool = False
    ingredient_lines: list[SaveIngredientLine] = Field(max_length=MAX_LINES + 1)
    steps: list[str] = Field(max_length=MAX_STEPS + 1)


class NameMatchesBody(BaseModel):
    names: list[str] = Field(min_length=1, max_length=MAX_LINES)


class NameMatch(BaseModel):
    name: str
    entry: str | None


class NameMatchesResponse(BaseModel):
    matches: list[NameMatch]


class RecipeLineResponse(BaseModel):
    name: str
    vague: bool
    quantity: float | None
    unit: str | None
    size: str | None
    preparation: str | None
    note: str | None


class RecipeNotebookResponse(BaseModel):
    id: UUID
    name: str
    kind: str
    kitchen_id: UUID | None


class RecipeSourceResponse(BaseModel):
    type: str
    url: str | None


class RecipeDetailResponse(BaseModel):
    id: UUID
    title: str
    base_servings: int
    servings_estimated: bool
    author_alias: str | None
    created_at: datetime
    version: datetime
    notebook: RecipeNotebookResponse
    can_write: bool
    ingredient_lines: list[RecipeLineResponse]
    steps: list[str]
    source: RecipeSourceResponse | None


class UpdateRecipeResponse(RecipeDetailResponse):
    created_catalog_names: list[str]
