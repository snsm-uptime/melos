"""Bodies for the kitchen shopping list (specs 023, 025, contracts/shopping-list-api.md)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Literal
from uuid import UUID

from application.shopping_list import (
    ClosedListSummary,
    ClosedListView,
    PlaceChoices,
    ShoppingListView,
)
from domain.cart import RecipeRef, ShoppingList, name_sort_key
from domain.ingredient_catalog import normalize_name
from domain.places import DefaultKey, PlaceRef, resolve_place
from domain.shopping_list import ListNames, SavedLine, shown_list_name
from pydantic import BaseModel, model_validator


class AmountResponse(BaseModel):
    quantity: str
    unit: str


class RecipeRefResponse(BaseModel):
    recipe_id: UUID
    title: str
    # False when a saved chip's recipe is gone.
    exists: bool = True


class PlaceResponse(BaseModel):
    """{kind: default, key} or {kind: custom, id, name} (spec 070 contracts/shopping-list.md)."""

    kind: Literal["default", "custom"]
    key: DefaultKey | None = None
    id: UUID | None = None
    name: str | None = None


class PlaceBody(BaseModel):
    kind: Literal["default", "custom"]
    key: str | None = None
    id: UUID | None = None

    @model_validator(mode="after")
    def _one(self) -> PlaceBody:
        if (self.kind == "default") != (self.key is not None) or (self.kind == "custom") != (
            self.id is not None
        ):
            raise ValueError("a default place needs key, a custom place needs id")
        return self

    def ref(self) -> PlaceRef:
        if self.kind == "default":
            return PlaceRef(key=self.key)  # type: ignore[arg-type]
        return PlaceRef(id=self.id)


class CustomPlaceResponse(BaseModel):
    id: UUID
    name: str


def place_response(place: PlaceRef) -> PlaceResponse:
    if place.key is not None:
        return PlaceResponse(kind="default", key=place.key)
    return PlaceResponse(kind="custom", id=place.id, name=place.name)


class ShoppingLineResponse(BaseModel):
    id: UUID | None = None
    bought: bool = False
    place: PlaceResponse | None = None
    # The word the viewer sees (spec 043 FR-007); kept_name is the line's key.
    name: str
    kept_name: str = ""
    kind: Literal["mass", "volume", "count", "custom"]
    size: Literal["small", "medium", "large"] | None
    amounts: list[AmountResponse]
    recipes: list[RecipeRefResponse]


class YourCallResponse(BaseModel):
    id: UUID | None = None
    bought: bool = False
    place: PlaceResponse | None = None
    name: str
    kept_name: str = ""
    notes: list[str]
    recipes: list[RecipeRefResponse]


class HandItemResponse(BaseModel):
    id: UUID
    bought: bool = False
    place: PlaceResponse | None = None
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
    custom_places: list[CustomPlaceResponse] = []


class AddShoppingItemBody(BaseModel):
    name: object = None
    quantity: object = None
    unit: object = None
    size: object = None
    place: PlaceBody | None = None


class SetBoughtBody(BaseModel):
    bought: bool


class CloseShoppingListBody(BaseModel):
    list_id: UUID
    # The member's local day; the UTC day when absent.
    closing_date: date | None = None


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
    custom_places: list[CustomPlaceResponse] = []


def _place(name: str, places: PlaceChoices | None) -> PlaceResponse | None:
    return None if places is None else place_response(resolve_place(name, places.choices))


def _place_any(
    kept: str, words: Mapping[str, str], places: PlaceChoices | None
) -> PlaceResponse | None:
    """The viewer's place under any of the line's names, kept name first (spec 043 FR-007a)."""
    if places is None:
        return None
    for name in (kept, *sorted(words.values())):
        if normalize_name(name) in places.choices:
            return place_response(resolve_place(name, places.choices))
    return _place(kept, places)


def _shown(kept: str, names: ListNames | None, language: str | None) -> str:
    return shown_list_name(kept, names or {}, language)


def _by_shown[T: (ShoppingLineResponse, YourCallResponse)](responses: list[T]) -> list[T]:
    # Stable: lines of one name keep their kind and size order (FR-007 sorts by the shown word).
    return sorted(responses, key=lambda response: name_sort_key(response.name))


def _custom(places: PlaceChoices | None) -> list[CustomPlaceResponse]:
    if places is None:
        return []
    return [CustomPlaceResponse(id=p.id, name=p.name) for p in places.custom]


def _stored(items: tuple[SavedLine, ...], section: str) -> list[SavedLine | None]:
    return [item for item in items if item.section == section]  # type: ignore[misc]


def _pad(stored: list[SavedLine | None], count: int) -> list[SavedLine | None]:
    """Stored lines matched to built lines by order; none when the list is not stored (R3)."""
    return stored if len(stored) == count else [None] * count


def _recipes(refs: tuple[RecipeRef, ...], missing: frozenset[UUID]) -> list[RecipeRefResponse]:
    return [
        RecipeRefResponse(recipe_id=r.recipe_id, title=r.title, exists=r.recipe_id not in missing)
        for r in refs
    ]


def _lines(
    result: ShoppingList,
    missing: frozenset[UUID],
    stored: tuple[SavedLine, ...] = (),
    places: PlaceChoices | None = None,
    names: ListNames | None = None,
    language: str | None = None,
) -> list[ShoppingLineResponse]:
    saved = _pad(_stored(stored, "measured"), len(result.lines))
    words = names or {}
    return _by_shown(
        [
            ShoppingLineResponse(
                id=item.id if item else None,
                bought=item.bought if item else False,
                place=_place_any(line.name, words.get(line.name, {}), places),
                name=_shown(line.name, names, language),
                kept_name=line.name,
                kind=line.kind,
                size=line.size,  # type: ignore[arg-type]
                amounts=[AmountResponse(quantity=a.quantity, unit=a.unit) for a in line.amounts],
                recipes=_recipes(line.recipes, missing),
            )
            for line, item in zip(result.lines, saved, strict=True)
        ]
    )


def _your_call(
    result: ShoppingList,
    missing: frozenset[UUID],
    stored: tuple[SavedLine, ...] = (),
    places: PlaceChoices | None = None,
    names: ListNames | None = None,
    language: str | None = None,
) -> list[YourCallResponse]:
    saved = _pad(_stored(stored, "your_call"), len(result.your_call))
    words = names or {}
    return _by_shown(
        [
            YourCallResponse(
                id=item.id if item else None,
                bought=item.bought if item else False,
                place=_place_any(e.name, words.get(e.name, {}), places),
                name=_shown(e.name, names, language),
                kept_name=e.name,
                notes=list(e.notes),
                recipes=_recipes(e.recipes, missing),
            )
            for e, item in zip(result.your_call, saved, strict=True)
        ]
    )


def _hand(
    items: tuple[SavedLine, ...], places: PlaceChoices | None = None
) -> list[HandItemResponse]:
    responses: list[HandItemResponse] = []
    for item in items:
        assert item.id is not None
        amount = item.amounts[0] if item.amounts else None
        responses.append(
            HandItemResponse(
                id=item.id,
                bought=item.bought,
                place=_place(item.name, places),
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
        lines=_lines(
            result,
            view.missing_recipe_ids,
            view.cart_items,
            view.places,
            view.names,
            view.language,
        ),
        your_call=_your_call(
            result,
            view.missing_recipe_ids,
            view.cart_items,
            view.places,
            view.names,
            view.language,
        ),
        hand_items=_hand(view.hand_items, view.places),
        custom_places=_custom(view.places),
    )


def closed_list_response(view: ClosedListView) -> ClosedListResponse:
    assert view.saved.closing_date is not None
    return ClosedListResponse(
        id=view.saved.id,
        closing_date=view.saved.closing_date,
        lines=_lines(
            view.shopping_list,
            view.missing_recipe_ids,
            view.cart_items,
            view.places,
            view.names,
            view.language,
        ),
        your_call=_your_call(
            view.shopping_list,
            view.missing_recipe_ids,
            view.cart_items,
            view.places,
            view.names,
            view.language,
        ),
        hand_items=_hand(view.hand_items, view.places),
        custom_places=_custom(view.places),
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
