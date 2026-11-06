"""Places to buy things (spec 070): a person's places, their place per ingredient, copying.

Everything here is about the caller's own data; another person is reached only through the copy,
and only when they share a kitchen or a personal notebook with the caller (research R8).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.errors import InvalidPlaceError, PlaceNotFoundError
from domain.ingredient_catalog import normalize_name
from domain.places import (
    DEFAULT_PLACE_KEYS,
    SUPERMARKET,
    CustomPlace,
    PlaceRef,
    check_new_name,
    fold,
    ingredient_key,
)

from application.ports import PlaceRepository, PlaceSource, RecipeUse

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PlacesView:
    defaults: tuple[str, ...]
    custom: tuple[CustomPlace, ...]


@dataclass(frozen=True, slots=True)
class IngredientRecipe:
    id: UUID
    title: str


@dataclass(frozen=True, slots=True)
class IngredientPlace:
    name: str
    place: PlaceRef
    # The readable recipes that use the name, newest first.
    recipes: tuple[IngredientRecipe, ...] = ()
    # When the newest of those recipes was made; None when no recipe uses it.
    last_used_at: datetime | None = None


class ListPlacesService:
    def __init__(self, places: PlaceRepository) -> None:
        self._places = places

    def execute(self, user_id: UUID) -> PlacesView:
        return PlacesView(DEFAULT_PLACE_KEYS, tuple(self._places.list_custom(user_id)))


class AddPlaceService:
    def __init__(self, places: PlaceRepository) -> None:
        self._places = places

    def execute(self, user_id: UUID, name: object) -> CustomPlace:
        keys = self._places.name_keys(user_id)
        clean = check_new_name(name, keys, count=len(keys))
        place = self._places.add(user_id, clean, fold(clean))
        logger.info("place outcome=added")
        return place


class RenamePlaceService:
    def __init__(self, places: PlaceRepository) -> None:
        self._places = places

    def execute(self, user_id: UUID, place_id: UUID, name: object) -> CustomPlace:
        clean = check_new_name(name, self._places.name_keys(user_id, except_id=place_id))
        place = self._places.rename(user_id, place_id, clean, fold(clean))
        if place is None:
            raise PlaceNotFoundError()
        return place


class DeletePlaceService:
    def __init__(self, places: PlaceRepository) -> None:
        self._places = places

    def execute(self, user_id: UUID, place_id: UUID) -> None:
        if not self._places.delete(user_id, place_id):
            raise PlaceNotFoundError()
        logger.info("place outcome=deleted")


def checked_place(places: PlaceRepository, user_id: UUID, place: PlaceRef) -> PlaceRef:
    """The place as stored: a known default key, or one of the caller's own places."""
    if place.key is not None:
        if place.key not in DEFAULT_PLACE_KEYS or place.id is not None:
            raise InvalidPlaceError()
        return PlaceRef(key=place.key)
    if place.id is None:
        raise InvalidPlaceError()
    for own in places.list_custom(user_id):
        if own.id == place.id:
            return PlaceRef(id=own.id, name=own.name)
    raise InvalidPlaceError()


def catalog_entries(
    names: Sequence[str],
    choices: dict[str, PlaceRef],
    uses: Sequence[RecipeUse] = (),
) -> list[IngredientPlace]:
    """One entry per normalized name, shown with its first catalog spelling, sorted (R7).

    Each entry lists the recipes that use the name (one per recipe, newest first) and the date of
    the newest one.
    """
    shown: dict[str, str] = {}
    for name in sorted(names, key=lambda n: (normalize_name(n), n)):
        key = normalize_name(name)
        if key:
            shown.setdefault(key, name)
    by_key: dict[str, dict[UUID, RecipeUse]] = {}
    for use in uses:
        key = normalize_name(use.name)
        if key in shown:
            by_key.setdefault(key, {}).setdefault(use.recipe_id, use)
    entries = []
    for key in sorted(shown, key=lambda k: (shown[k].casefold(), k)):
        # Newest first; same-moment recipes by title, so the order never shifts between loads.
        recipes = sorted(by_key.get(key, {}).values(), key=lambda u: u.title.casefold())
        recipes.sort(key=lambda u: u.used_at, reverse=True)
        entries.append(
            IngredientPlace(
                shown[key],
                choices.get(key, SUPERMARKET),
                tuple(IngredientRecipe(u.recipe_id, u.title) for u in recipes),
                recipes[0].used_at if recipes else None,
            )
        )
    return entries


class IngredientPlacesService:
    def __init__(self, places: PlaceRepository) -> None:
        self._places = places

    def execute(self, user_id: UUID) -> list[IngredientPlace]:
        return catalog_entries(
            self._places.catalog_names(user_id),
            self._places.choices(user_id),
            self._places.recipe_uses(user_id),
        )


class SetIngredientPlaceService:
    def __init__(self, places: PlaceRepository) -> None:
        self._places = places

    def execute(self, user_id: UUID, name: object, place: PlaceRef) -> IngredientPlace:
        key = ingredient_key(name)
        stored = checked_place(self._places, user_id, place)
        self._places.set_choice(user_id, key, stored)
        return IngredientPlace(key, stored)


class PlaceSourcesService:
    def __init__(self, places: PlaceRepository) -> None:
        self._places = places

    def execute(self, user_id: UUID) -> Sequence[PlaceSource]:
        return self._places.sources(user_id)


class CopyPlacesService:
    """Replace the caller's places with a snapshot of another member's (FR-010a)."""

    def __init__(self, places: PlaceRepository) -> None:
        self._places = places

    def execute(self, user_id: UUID, source_id: UUID) -> PlacesView:
        if source_id == user_id or all(
            s.user_id != source_id for s in self._places.sources(user_id)
        ):
            raise PlaceNotFoundError()
        self._places.replace_with_copy(user_id, source_id)
        logger.info("places outcome=copied")
        return ListPlacesService(self._places).execute(user_id)
