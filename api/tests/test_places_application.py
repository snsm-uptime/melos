"""Place use cases against a fake repository (spec 070 US2, contracts/places.md)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import replace
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
from application.ports import PlaceSource
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

    def sources(self, user_id: UUID) -> Sequence[PlaceSource]:
        return self.shared.get(user_id, [])

    def replace_with_copy(self, target_id: UUID, source_id: UUID) -> None:
        for place_id in [i for i, (owner, _) in self.places.items() if owner == target_id]:
            del self.places[place_id]
        new_ids = {}
        for owner, place in list(self.places.values()):
            if owner == source_id:
                copy = self.add(target_id, place.name, fold(place.name))
                new_ids[place.id] = copy.id
        self.chosen[target_id] = {
            name: ref if ref.id is None else PlaceRef(id=new_ids[ref.id])
            for name, ref in self.chosen.get(source_id, {}).items()
        }


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


def test_copy_is_a_snapshot_and_needs_a_shared_kitchen() -> None:
    repo = FakePlaces()
    asian = AddPlaceService(repo).execute(ANA, "Asian market")
    SetIngredientPlaceService(repo).execute(ANA, "miso", PlaceRef(id=asian.id))
    AddPlaceService(repo).execute(BEN, "Old place")
    with pytest.raises(PlaceNotFoundError):
        CopyPlacesService(repo).execute(BEN, ANA)

    repo.shared[BEN] = [PlaceSource(ANA, "ana")]
    view = CopyPlacesService(repo).execute(BEN, ANA)
    assert [p.name for p in view.custom] == ["Asian market"]
    assert repo.choices(BEN)["miso"].name == "Asian market"

    RenamePlaceService(repo).execute(ANA, asian.id, "Japanese market")
    assert repo.choices(BEN)["miso"].name == "Asian market"
