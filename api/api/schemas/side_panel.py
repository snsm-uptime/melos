"""Request and response bodies for the side panel (spec 064, contracts/side-panel-api.md)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class SidePanelResponse(BaseModel):
    default_kitchen_id: UUID | None
    recipes_added: int
    notebooks: int


class SetDefaultKitchenBody(BaseModel):
    kitchen_id: UUID
