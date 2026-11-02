"""Pydantic DTOs for notebooks (specs 056 and 035)."""

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
    origin_notebook_name: str | None
    is_snapshot: bool
    is_own_capture_notebook: bool


class CreateNotebookRequest(BaseModel):
    """A new personal notebook (S-059). The name's rules are in the domain."""

    name: str


class NameNotebookRequest(BaseModel):
    """A new name, or the name of a new kitchen notebook (spec 059). Its rules are in the domain."""

    name: str


class AddNotebookSnapshotRequest(BaseModel):
    """Add a personal notebook to a kitchen (spec 035, contracts/snapshots-api.md)."""

    source_notebook_id: UUID
    snapshot_key: UUID
    confirm_repeat: bool = False


class NotebooksResponse(BaseModel):
    notebooks: list[NotebookResponse]
