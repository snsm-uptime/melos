"""Request bodies for the recipe capture routes (spec 016 and spec 026 contracts)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CaptureTextBody(BaseModel):
    text: str


class CaptureUrlBody(BaseModel):
    # A guard: the link rules then allow 2,048 characters (spec 026 contracts/capture-url-api.md).
    url: str = Field(max_length=4096)


class UnitCheckBody(BaseModel):
    word: str = Field(max_length=200)
