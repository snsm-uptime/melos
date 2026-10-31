"""Pydantic DTOs for notebook reads (spec 056, contracts/notebooks-api.md)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class NotebookResponse(BaseModel):
    """One notebook as the caller may see it. The same shape for every route and kind."""

    id: UUID
    name: str
    kind: Literal["personal", "kitchen"]
    access: Literal["owner", "member", "kitchen_member"]
    owner_alias: str | None
    kitchen_id: UUID | None
    kitchen_is_archived: bool | None
    is_default: bool
    recipe_count: int


class NotebooksResponse(BaseModel):
    notebooks: list[NotebookResponse]
