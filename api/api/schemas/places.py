"""Bodies for a person's places (spec 070 contracts/places.md)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from application.places import IngredientPlace, PlacesView
from pydantic import BaseModel

from api.schemas.shopping_list import (
    CustomPlaceResponse,
    PlaceBody,
    PlaceResponse,
    place_response,
)


class PlacesResponse(BaseModel):
    defaults: list[str]
    custom: list[CustomPlaceResponse]


class PlaceNameBody(BaseModel):
    name: object = None


class IngredientRecipeResponse(BaseModel):
    id: UUID
    title: str


class IngredientPlaceResponse(BaseModel):
    name: str
    place: PlaceResponse
    recipes: list[IngredientRecipeResponse] = []
    last_used_at: datetime | None = None
    # Spec 043: the ingredient's other names, shown under it.
    other_names: list[str] = []


class IngredientPlacesResponse(BaseModel):
    items: list[IngredientPlaceResponse]


class SetIngredientPlaceBody(BaseModel):
    name: object = None
    place: PlaceBody


class PlaceSourceResponse(BaseModel):
    user_id: UUID
    alias: str


class PlaceSourcesResponse(BaseModel):
    items: list[PlaceSourceResponse]


class CopyPlacesBody(BaseModel):
    source_user_id: UUID


def places_response(view: PlacesView) -> PlacesResponse:
    return PlacesResponse(
        defaults=list(view.defaults),
        custom=[CustomPlaceResponse(id=p.id, name=p.name) for p in view.custom],
    )


def ingredient_place_response(item: IngredientPlace) -> IngredientPlaceResponse:
    return IngredientPlaceResponse(
        name=item.name,
        place=place_response(item.place),
        recipes=[IngredientRecipeResponse(id=r.id, title=r.title) for r in item.recipes],
        last_used_at=item.last_used_at,
        other_names=list(item.other_names),
    )
