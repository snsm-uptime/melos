"""Request body for saving a recipe (spec 020, contracts/save-api.md)."""

from __future__ import annotations

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
