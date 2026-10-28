"""Pydantic DTOs for recipe lists (spec 021, contracts/list-api.md)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RecipeCardResponse(BaseModel):
    id: UUID
    title: str
    author_alias: str | None
    ingredient_count: int
    notebook_id: UUID
    notebook_name: str
    created_at: datetime


class RecipePageResponse(BaseModel):
    items: list[RecipeCardResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
