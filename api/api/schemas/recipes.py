"""Request and response bodies for recipes (spec 020 save, spec 027 detail, edit, delete)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from domain.recipe import MAX_LINES, MAX_STEPS
from pydantic import BaseModel, Field

from api.schemas.carts import EditorResponse


class SaveIngredientLine(BaseModel):
    name: str
    vague: bool = False
    quantity: float | None = None
    unit: str | None = None
    size: str | None = None
    preparation: str | None = None
    vague_text: str | None = None
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
    keep_units: list[str] = Field(default_factory=list, max_length=MAX_LINES + 1)
    # Link capture (spec 026): the page address instead of pasted text, and its photo.
    source_url: str | None = Field(default=None, max_length=2048)
    preview_image: str | None = None
    # The draft's language (spec 043 FR-005a); left out stores Spanish.
    language: Literal["en", "es"] | None = None
    # "photo" for a picture draft (spec 041); left out means text, or url when source_url is set.
    source_kind: Literal["text", "url", "photo"] | None = None


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
    keep_units: list[str] = Field(default_factory=list, max_length=MAX_LINES + 1)
    # The image (S-067): left out keeps it, null removes it, a data URI replaces it.
    preview_image: str | None = None
    # Spec 043: a language replaces the stored one and clears a proposal; left out keeps it.
    language: Literal["en", "es"] | None = None
    # Sent as null alone to dismiss the model's proposal (FR-005a).
    proposed_language: None = None


class SetRecipeLanguageBody(BaseModel):
    """Apply a language, which clears the proposal, or send null to dismiss it (spec 043)."""

    language: Literal["en", "es"] | None


class NameMatchesBody(BaseModel):
    names: list[str] = Field(min_length=1, max_length=MAX_LINES)


class NameMatch(BaseModel):
    name: str
    entry: str | None


class NameMatchesResponse(BaseModel):
    matches: list[NameMatch]


class RecipeLineResponse(BaseModel):
    # The kept name, as the line is stored.
    name: str
    # The name in the recipe's language (spec 043 FR-006).
    shown_name: str
    vague: bool
    quantity: float | None
    unit: str | None
    size: str | None
    preparation: str | None
    vague_text: str | None
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
    # The recipe image as a data URI (spec 026); null when it has none.
    preview_image: str | None = None
    # 'en' or 'es', and the model's differing proposal or null (spec 043 FR-005a).
    language: str = "es"
    proposed_language: str | None = None
    # Who edits the recipe now (spec 022); null when nobody does.
    editor: EditorResponse | None = None
    # Kitchen recipes only (null for personal notebooks): in the cart as the caller sees it,
    # and who edits the cart.
    in_cart: bool | None = None
    cart_editor: EditorResponse | None = None


class RecipeLockResponse(BaseModel):
    editor: EditorResponse


class UpdateRecipeResponse(RecipeDetailResponse):
    created_catalog_names: list[str]


class ShareCandidate(BaseModel):
    user_id: UUID
    alias: str


class ShareCandidatesResponse(BaseModel):
    candidates: list[ShareCandidate]


class ShareRequest(BaseModel):
    recipient_user_id: UUID


class ShareResponse(BaseModel):
    recipe_id: UUID
    recipient_alias: str
    notebook_id: UUID
