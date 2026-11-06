"""Place use cases against a fake repository (spec 070 US2, contracts/places.md)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest
from application.places import (
    AddPlaceService,
    CopyPlacesService,
    DeletePlaceService,
    IngredientPlacesService,
    RenamePlaceService,
    SetIngredientPlaceService,
)
from application.ports import PlaceSource, RecipeUse
from domain.errors import (
    IngredientNameInvalidError,
    InvalidPlaceError,
    PlaceLimitError,
    PlaceNameTakenError,
    PlaceNotFoundError,
)
from domain.places import SUPERMARKET, CustomPlace, PlaceRef, fold


class FakePlaces:
    def __init__(self) -> None:
        self.places: dict[UUID, tuple[UUID, CustomPlace]] = {}
        self.chosen: dict[UUID, dict[str, PlaceRef]] = {}
        self.catalog: dict[UUID, list[str]] = {}
        self.shared: dict[UUID, list[PlaceSource]] = {}
        self.uses: dict[UUID, list[RecipeUse]] = {}

    def list_custom(self, user_id: UUID) -> Sequence[CustomPlace]:
        mine = [p for owner, p in self.places.values() if owner == user_id]
        return sorted(mine, key=lambda p: fold(p.name))

    def name_keys(self, user_id: UUID, *, except_id: UUID | None = None) -> set[str]:
        return {fold(p.name) for p in self.list_custom(user_id) if p.id != except_id}

    def add(self, user_id: UUID, name: str, name_key: str) -> CustomPlace:
        place = CustomPlace(uuid.uuid4(), name)
        self.places[place.id] = (user_id, place)
        return place

    def rename(self, user_id: UUID, place_id: UUID, name: str, name_key: str) -> CustomPlace | None:
        found = self.places.get(place_id)
        if found is None or found[0] != user_id:
            return None
        self.places[place_id] = (user_id, CustomPlace(place_id, name))
        return self.places[place_id][1]

    def delete(self, user_id: UUID, place_id: UUID) -> bool:
        found = self.places.get(place_id)
        if found is None or found[0] != user_id:
            return False
        del self.places[place_id]
        mine = self.chosen.get(user_id, {})
        for name in [n for n, ref in mine.items() if ref.id == place_id]:
            del mine[name]
        return True

    def choices(self, user_id: UUID) -> dict[str, PlaceRef]:
        result = {}
        for name, ref in self.chosen.get(user_id, {}).items():
            if ref.id is not None:
                ref = replace(ref, name=self.places[ref.id][1].name)
            result[name] = ref
        return result

    def set_choice(self, user_id: UUID, name: str, place: PlaceRef) -> None:
        self.chosen.setdefault(user_id, {})[name] = place

    def catalog_names(self, user_id: UUID) -> Sequence[str]:
        return [*self.catalog.get(user_id, []), *self.chosen.get(user_id, {})]

    def recipe_uses(self, user_id: UUID) -> Sequence[RecipeUse]:
        return self.uses.get(user_id, [])

    def sources(self, user_id: UUID) -> Sequence[PlaceSource]:
        return self.shared.get(user_id, [])


ANA = uuid.uuid4()
BEN = uuid.uuid4()


def test_add_rename_and_refusals() -> None:
    repo = FakePlaces()
    asian = AddPlaceService(repo).execute(ANA, "Asian market")
    with pytest.raises(PlaceNameTakenError):
        AddPlaceService(repo).execute(ANA, "ASIAN MARKET")
    with pytest.raises(PlaceNameTakenError):
        AddPlaceService(repo).execute(ANA, "Supermercado")
    # The same name for someone else is fine.
    AddPlaceService(repo).execute(BEN, "Asian market")
    # Renaming to its own name with other letter case is allowed.
    assert RenamePlaceService(repo).execute(ANA, asian.id, "asian Market").name == "asian Market"
    with pytest.raises(PlaceNotFoundError):
        RenamePlaceService(repo).execute(BEN, asian.id, "Mine")
    with pytest.raises(PlaceNotFoundError):
        DeletePlaceService(repo).execute(BEN, asian.id)


def test_limit_of_30() -> None:
    repo = FakePlaces()
    for i in range(30):
        AddPlaceService(repo).execute(ANA, f"Shop {i}")
    with pytest.raises(PlaceLimitError):
        AddPlaceService(repo).execute(ANA, "One more")


def test_set_place_and_catalog_page() -> None:
    repo = FakePlaces()
    repo.catalog[ANA] = ["tomato", "Miso", "flour", "tomato"]
    asian = AddPlaceService(repo).execute(ANA, "Asian market")
    SetIngredientPlaceService(repo).execute(ANA, "Tomato", PlaceRef(key="farmers_market"))
    SetIngredientPlaceService(repo).execute(ANA, "miso", PlaceRef(id=asian.id))
    items = IngredientPlacesService(repo).execute(ANA)
    assert [(i.name, i.place.key or i.place.name) for i in items] == [
        ("flour", "supermarket"),
        ("Miso", "Asian market"),
        ("tomato", "farmers_market"),
    ]
    DeletePlaceService(repo).execute(ANA, asian.id)
    miso = next(i for i in IngredientPlacesService(repo).execute(ANA) if i.name == "Miso")
    assert miso.place == SUPERMARKET


def test_catalog_page_lists_recipes_and_last_use() -> None:
    repo = FakePlaces()
    repo.catalog[ANA] = ["tomato", "flour"]
    soup, salad = uuid.uuid4(), uuid.uuid4()
    old, new = datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 3, 1, tzinfo=UTC)
    repo.uses[ANA] = [
        RecipeUse("Tomato", soup, "Soup", old),
        RecipeUse("tomato ", soup, "Soup", old),  # the same recipe twice counts once
        RecipeUse("tomato", salad, "Salad", new),
        RecipeUse("basil", salad, "Salad", new),  # not in the catalog: ignored
    ]
    items = {i.name: i for i in IngredientPlacesService(repo).execute(ANA)}
    assert [r.title for r in items["tomato"].recipes] == ["Salad", "Soup"]
    assert items["tomato"].recipes[0].id == salad
    assert items["tomato"].last_used_at == new
    assert items["flour"].recipes == ()
    assert items["flour"].last_used_at is None


def test_invalid_places_and_names() -> None:
    repo = FakePlaces()
    bens = AddPlaceService(repo).execute(BEN, "Deli")
    service = SetIngredientPlaceService(repo)
    with pytest.raises(InvalidPlaceError):
        service.execute(ANA, "tomato", PlaceRef(id=bens.id))
    with pytest.raises(InvalidPlaceError):
        service.execute(ANA, "tomato", PlaceRef(key="moon"))  # type: ignore[arg-type]
    with pytest.raises(IngredientNameInvalidError):
        service.execute(ANA, "  ", PlaceRef(key="bakery"))


def test_copy_adds_only_new_places_and_choices_and_needs_a_shared_kitchen() -> None:
    repo = FakePlaces()
    asian = AddPlaceService(repo).execute(ANA, "Asian market")
    ana_deli = AddPlaceService(repo).execute(ANA, "deli")
    SetIngredientPlaceService(repo).execute(ANA, "miso", PlaceRef(id=asian.id))
    SetIngredientPlaceService(repo).execute(ANA, "ham", PlaceRef(id=ana_deli.id))
    SetIngredientPlaceService(repo).execute(ANA, "tomato", PlaceRef(key="farmers_market"))
    SetIngredientPlaceService(repo).execute(ANA, "bread", PlaceRef(key="bakery"))

    old = AddPlaceService(repo).execute(BEN, "Old place")
    ben_deli = AddPlaceService(repo).execute(BEN, "Deli")
    SetIngredientPlaceService(repo).execute(BEN, "tomato", PlaceRef(id=old.id))
    with pytest.raises(PlaceNotFoundError):
        CopyPlacesService(repo).execute(BEN, ANA)

    repo.shared[BEN] = [PlaceSource(ANA, "ana")]
    view = CopyPlacesService(repo).execute(BEN, ANA)
    # Ben's own places stay; only a name he lacks is added ("deli" is his "Deli").
    assert sorted(p.name for p in view.custom) == ["Asian market", "Deli", "Old place"]
    chosen = repo.choices(BEN)
    # His own choice stays; new ones are copied, a custom one pointing at his same-named place.
    assert chosen["tomato"].id == old.id
    assert chosen["bread"].key == "bakery"
    assert chosen["miso"].name == "Asian market"
    assert chosen["ham"].id == ben_deli.id

    # Copying again adds nothing new.
    again = CopyPlacesService(repo).execute(BEN, ANA)
    assert len(again.custom) == 3

    RenamePlaceService(repo).execute(ANA, asian.id, "Japanese market")
    assert repo.choices(BEN)["miso"].name == "Asian market"


def test_copy_stops_at_the_place_limit_and_skips_choices_of_places_not_added() -> None:
    repo = FakePlaces()
    for i in range(29):
        AddPlaceService(repo).execute(BEN, f"Mine {i}")
    first = AddPlaceService(repo).execute(ANA, "A shop")
    second = AddPlaceService(repo).execute(ANA, "B shop")
    SetIngredientPlaceService(repo).execute(ANA, "rice", PlaceRef(id=first.id))
    SetIngredientPlaceService(repo).execute(ANA, "salt", PlaceRef(id=second.id))
    repo.shared[BEN] = [PlaceSource(ANA, "ana")]
    view = CopyPlacesService(repo).execute(BEN, ANA)
    assert len(view.custom) == 30
    added = {p.name for p in view.custom} - {f"Mine {i}" for i in range(29)}
    chosen = repo.choices(BEN)
    # Only the place that fit is used; the other's choice is skipped, not pointed elsewhere.
    assert len(added) == 1
    assert {chosen[n].name for n in chosen} == added
