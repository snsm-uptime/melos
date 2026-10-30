"""Response body for the kitchen shopping list (spec 023, contracts/shopping-list-api.md)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from application.shopping_list import ShoppingListView
from domain.cart import RecipeRef
from pydantic import BaseModel


class AmountResponse(BaseModel):
    quantity: str
    unit: str


class RecipeRefResponse(BaseModel):
    recipe_id: UUID
    title: str


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


class ShoppingListResponse(BaseModel):
    is_empty: bool
    lines: list[ShoppingLineResponse]
    your_call: list[YourCallResponse]


def _recipes(refs: tuple[RecipeRef, ...]) -> list[RecipeRefResponse]:
    return [RecipeRefResponse(recipe_id=r.recipe_id, title=r.title) for r in refs]


def shopping_list_response(view: ShoppingListView) -> ShoppingListResponse:
    result = view.shopping_list
    return ShoppingListResponse(
        is_empty=view.is_empty,
        lines=[
            ShoppingLineResponse(
                name=line.name,
                kind=line.kind,
                size=line.size,  # type: ignore[arg-type]
                amounts=[AmountResponse(quantity=a.quantity, unit=a.unit) for a in line.amounts],
                recipes=_recipes(line.recipes),
            )
            for line in result.lines
        ],
        your_call=[
            YourCallResponse(name=e.name, notes=list(e.notes), recipes=_recipes(e.recipes))
            for e in result.your_call
        ],
    )
