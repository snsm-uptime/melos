"""Pydantic DTOs for notebook reads (spec 055)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class KitchenNotebookResponse(BaseModel):
    id: UUID
    kind: Literal["kitchen"] = "kitchen"
    kitchen_id: UUID
    # A kitchen notebook has no stored name; it shows the kitchen's.
    name: str
    is_archived: bool


class MemberNotebookResponse(BaseModel):
    """Same shape whether the default notebook was just created or already existed."""

    id: UUID
    kind: Literal["member"] = "member"
    user_id: UUID
