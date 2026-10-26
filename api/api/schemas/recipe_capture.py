"""Request body for the recipe capture route (spec 016, contracts/capture-api.md)."""

from __future__ import annotations

from pydantic import BaseModel


class CaptureTextBody(BaseModel):
    text: str
