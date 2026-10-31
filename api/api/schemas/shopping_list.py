"""Bodies for the kitchen shopping list (specs 023, 025, contracts/shopping-list-api.md)."""

from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from application.shopping_list import (
    ClosedListSummary,
    ClosedListView,
    ShoppingListView,
)
from domain.cart import RecipeRef, ShoppingList
from domain.shopping_list import SavedLine
from pydantic import BaseModel


class AmountResponse(BaseModel):
    quantity: str
    unit: str


class RecipeRefResponse(BaseModel):
    recipe_id: UUID
    title: str
    # False when a saved chip's recipe is gone.
    exists: bool = True


class ShoppingLineResponse(BaseModel):
    name: str
    kind: Literal["mass", "volume", "count"]
    size: Literal["small", "medium", "large"] | None
    amounts: list[AmountResponse]
    recipes: list[RecipeRefResponse]


class YourCallResponse(BaseModel):
    name: str
    notes: list[str]
    recipes: list[RecipeRefResponse]


class HandItemResponse(BaseModel):
    id: UUID
    name: str
    quantity: str | None
    unit: str | None
    size: Literal["small", "medium", "large"] | None


class ShoppingListResponse(BaseModel):
    is_empty: bool
    status: Literal["live", "active", "draft"]
    list_id: UUID | None
    kitchen_is_archived: bool
    lines: list[ShoppingLineResponse]
    your_call: list[YourCallResponse]
    hand_items: list[HandItemResponse]


class AddShoppingItemBody(BaseModel):
    name: object = None
    quantity: object = None
    unit: object = None
    size: object = None


class CloseShoppingListBody(BaseModel):
    list_id: UUID


class ClosedListSummaryResponse(BaseModel):
    id: UUID
    closing_date: date
    recipe_titles: list[str]


class ClosedListsResponse(BaseModel):
    items: list[ClosedListSummaryResponse]


class ClosedListResponse(BaseModel):
    id: UUID
    closing_date: date
    lines: list[ShoppingLineResponse]
    your_call: list[YourCallResponse]
    hand_items: list[HandItemResponse]


def _recipes(refs: tuple[RecipeRef, ...], missing: frozenset[UUID]) -> list[RecipeRefResponse]:
    return [
        RecipeRefResponse(recipe_id=r.recipe_id, title=r.title, exists=r.recipe_id not in missing)
        for r in refs
    ]


def _lines(result: ShoppingList, missing: frozenset[UUID]) -> list[ShoppingLineResponse]:
    return [
        ShoppingLineResponse(
            name=line.name,
            kind=line.kind,
            size=line.size,  # type: ignore[arg-type]
            amounts=[AmountResponse(quantity=a.quantity, unit=a.unit) for a in line.amounts],
            recipes=_recipes(line.recipes, missing),
        )
        for line in result.lines
    ]


def _your_call(result: ShoppingList, missing: frozenset[UUID]) -> list[YourCallResponse]:
    return [
        YourCallResponse(name=e.name, notes=list(e.notes), recipes=_recipes(e.recipes, missing))
        for e in result.your_call
    ]


def _hand(items: tuple[SavedLine, ...]) -> list[HandItemResponse]:
    responses: list[HandItemResponse] = []
    for item in items:
        assert item.id is not None
        amount = item.amounts[0] if item.amounts else None
        responses.append(
            HandItemResponse(
                id=item.id,
                name=item.name,
                quantity=amount.quantity if amount else None,
                unit=amount.unit if amount else None,
                size=item.size,  # type: ignore[arg-type]
            )
        )
    return responses


def shopping_list_response(view: ShoppingListView) -> ShoppingListResponse:
    result = view.shopping_list
    return ShoppingListResponse(
        is_empty=view.is_empty,
        status=view.status,
        list_id=view.list_id,
        kitchen_is_archived=view.kitchen_is_archived,
        lines=_lines(result, view.missing_recipe_ids),
        your_call=_your_call(result, view.missing_recipe_ids),
        hand_items=_hand(view.hand_items),
    )


def closed_list_response(view: ClosedListView) -> ClosedListResponse:
    assert view.saved.closing_date is not None
    return ClosedListResponse(
        id=view.saved.id,
        closing_date=view.saved.closing_date,
        lines=_lines(view.shopping_list, view.missing_recipe_ids),
        your_call=_your_call(view.shopping_list, view.missing_recipe_ids),
        hand_items=_hand(view.hand_items),
    )


def closed_lists_response(items: tuple[ClosedListSummary, ...]) -> ClosedListsResponse:
    return ClosedListsResponse(
        items=[
            ClosedListSummaryResponse(
                id=s.id,
                closing_date=s.closing_date,
                recipe_titles=list(s.recipe_titles),
            )
            for s in items
        ]
    )
