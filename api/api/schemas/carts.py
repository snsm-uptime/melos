"""Request and response bodies for the kitchen cart (spec 022, contracts/cart-api.md)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from application.carts import MAX_ITEMS, CartDraftView, CartEntryView, CartView, EditorView
from pydantic import BaseModel, Field


class CartEntryResponse(BaseModel):
    recipe_id: UUID
    title: str
    notebook_id: UUID
    notebook_name: str
    base_servings: int
    meals: int
    factor: str


class EditorResponse(BaseModel):
    alias: str | None
    is_me: bool
    idle_expires_at: datetime | None = None


class CartDraftResponse(BaseModel):
    people: int
    people_is_default: bool
    entries: list[CartEntryResponse]
    dropped_recipe_ids: list[UUID]


class CartResponse(BaseModel):
    kitchen_id: UUID
    people: int
    people_is_default: bool
    entries: list[CartEntryResponse]
    editor: EditorResponse | None
    draft: CartDraftResponse | None
    can_edit: bool


class CartSaveResponse(CartResponse):
    dropped_recipe_ids: list[UUID]


class CartDraftItemBody(BaseModel):
    recipe_id: UUID
    # Checked by the use case, so a bad value answers invalid_value with its field.
    meals: object = None


class CartDraftBody(BaseModel):
    people: object = None
    items: list[CartDraftItemBody] = Field(max_length=MAX_ITEMS)


class AddDraftItemBody(BaseModel):
    recipe_id: UUID


def _entry(entry: CartEntryView) -> CartEntryResponse:
    return CartEntryResponse(
        recipe_id=entry.recipe_id,
        title=entry.title,
        notebook_id=entry.notebook_id,
        notebook_name=entry.notebook_name,
        base_servings=entry.base_servings,
        meals=entry.meals,
        factor=entry.factor,
    )


def editor_response(editor: EditorView | None) -> EditorResponse | None:
    if editor is None:
        return None
    return EditorResponse(
        alias=editor.alias, is_me=editor.is_me, idle_expires_at=editor.idle_expires_at
    )


def _draft(draft: CartDraftView | None) -> CartDraftResponse | None:
    if draft is None:
        return None
    return CartDraftResponse(
        people=draft.people,
        people_is_default=draft.people_is_default,
        entries=[_entry(e) for e in draft.entries],
        dropped_recipe_ids=list(draft.dropped_recipe_ids),
    )


def cart_response(view: CartView) -> CartResponse:
    return CartResponse(
        kitchen_id=view.kitchen_id,
        people=view.people,
        people_is_default=view.people_is_default,
        entries=[_entry(e) for e in view.entries],
        editor=editor_response(view.editor),
        draft=_draft(view.draft),
        can_edit=view.can_edit,
    )
