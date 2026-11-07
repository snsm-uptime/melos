"""Request and response bodies for catalog management (spec 043 contracts/catalog.md)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from application.catalog_manage import CatalogItem, CatalogView
from pydantic import BaseModel, Field

LanguageField = Literal["en", "es"]
NAME_MAX = 200


class VariantResponse(BaseModel):
    name: str
    language: LanguageField


class CatalogIngredientResponse(BaseModel):
    name: str
    language: LanguageField | None
    recipe_count: int
    variants: list[VariantResponse]
    spellings: list[str]


class CatalogResponse(BaseModel):
    notebook_id: UUID
    can_write: bool
    ingredients: list[CatalogIngredientResponse]


class RenameBody(BaseModel):
    new_name: str = Field(max_length=NAME_MAX)
    # Left out keeps the language; null clears it (FR-012).
    language: LanguageField | None = None


class RenameResponse(CatalogIngredientResponse):
    recipes_changed: int


class MergePreviewBody(BaseModel):
    from_notebook_id: UUID
    merged: str = Field(min_length=1, max_length=NAME_MAX)
    kept: str = Field(min_length=1, max_length=NAME_MAX)


class MergeNotebookResponse(BaseModel):
    notebook_id: UUID
    name: str
    recipe_count: int


class MergePreviewResponse(BaseModel):
    merged: str
    kept: str
    merged_language: LanguageField | None
    kept_language: LanguageField | None
    notebooks: list[MergeNotebookResponse]


class MergeBody(BaseModel):
    merged: str = Field(min_length=1, max_length=NAME_MAX)
    kept: str = Field(min_length=1, max_length=NAME_MAX)
    merged_language: LanguageField | None = None
    kept_language: LanguageField | None = None
    notebook_ids: list[UUID] = Field(min_length=1, max_length=200)


class MergedNotebook(BaseModel):
    notebook_id: UUID
    recipes_changed: int


class SkippedNotebook(BaseModel):
    notebook_id: UUID
    reason: Literal["name_changed", "no_access"]


class MergeResponse(BaseModel):
    merged: list[MergedNotebook]
    skipped: list[SkippedNotebook]


class SplitBody(BaseModel):
    other_name: str = Field(min_length=1, max_length=NAME_MAX)


class SplitResponse(BaseModel):
    kept: CatalogIngredientResponse
    split: CatalogIngredientResponse
    recipes_changed: int


class PairBody(BaseModel):
    en: str = Field(min_length=1, max_length=NAME_MAX)
    es: str = Field(min_length=1, max_length=NAME_MAX)


class PairSuggestionsResponse(BaseModel):
    pairs: list[PairBody]


def ingredient_response(item: CatalogItem) -> CatalogIngredientResponse:
    return CatalogIngredientResponse(
        name=item.name,
        language=item.language,
        recipe_count=item.recipe_count,
        variants=[
            VariantResponse(name=name, language=language)
            for language, name in sorted(item.variants.items())
        ],
        spellings=list(item.spellings),
    )


def catalog_response(view: CatalogView) -> CatalogResponse:
    return CatalogResponse(
        notebook_id=view.notebook_id,
        can_write=view.can_write,
        ingredients=[ingredient_response(item) for item in view.items],
    )
