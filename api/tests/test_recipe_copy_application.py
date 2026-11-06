"""Copying a personal recipe into a kitchen against fake ports (spec 069)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from application.ports import KitchenRecipeCopy, LockHolder, RecipeDetail, RecipeLineDetail
from application.recipe_copy import CopyRecipeToKitchenCommand, CopyRecipeToKitchenService
from domain.errors import (
    KitchenArchivedError,
    KitchenNotFoundError,
    RecipeAlreadyInKitchenError,
    RecipeLockedError,
    RecipeNotFoundError,
)
from tests.embedding_fakes import FakeEmbeddingJobs
from tests.test_notebooks_application import World, _join, _kitchen, _personal, _world

ANA, BEN = uuid4(), uuid4()
NOW = datetime(2026, 11, 4, tzinfo=UTC)


def _line(name: str) -> RecipeLineDetail:
    return RecipeLineDetail(
        name=name, vague=False, quantity=1, unit="cup", size=None, preparation=None, note=None
    )


@dataclass
class FakeRecipes:
    world: World
    details: dict[UUID, RecipeDetail] = field(default_factory=dict)
    # copy id -> (source id, notebook id, author id), in creation order
    copies: dict[UUID, tuple[UUID, UUID, UUID]] = field(default_factory=dict)
    overwrites: list[tuple[UUID, UUID, UUID]] = field(default_factory=list)

    def add(self, notebook_id: UUID, *names: str) -> UUID:
        recipe_id = uuid4()
        self.details[recipe_id] = RecipeDetail(
            id=recipe_id,
            notebook_id=notebook_id,
            title="Lentil soup",
            base_servings=4,
            servings_estimated=False,
            author_alias="ana",
            lines=tuple(_line(n) for n in names),
            steps=("Cook.",),
            source_type="text",
            source_url=None,
            created_at=NOW,
            updated_at=NOW,
        )
        return recipe_id

    def get_detail(self, recipe_id: UUID) -> RecipeDetail | None:
        return self.details.get(recipe_id)

    def copy_one(self, source: UUID, target: UUID, author: UUID) -> UUID | None:
        if source not in self.details:
            return None
        copy_id = uuid4()
        self.copies[copy_id] = (source, target, author)
        return copy_id

    def overwrite_from(self, target: UUID, source: UUID, author: UUID) -> bool:
        self.overwrites.append((target, source, author))
        return source in self.details

    def latest_copy_in_kitchen(self, source: UUID, kitchen_id: UUID) -> KitchenRecipeCopy | None:
        found = None
        for copy_id, (from_id, notebook_id, _author) in self.copies.items():
            notebook = self.world.notebooks.notebooks[notebook_id]
            if from_id == source and notebook.kitchen_id == kitchen_id:
                found = KitchenRecipeCopy(copy_id, notebook_id, notebook.name)
        return found


@dataclass
class FakeLocks:
    holders: dict[UUID, LockHolder] = field(default_factory=dict)

    def lock_recipe_row(self, recipe_id: UUID) -> bool:
        return True

    def recipe_holder(self, recipe_id: UUID) -> LockHolder | None:
        return self.holders.get(recipe_id)


@pytest.fixture
def world() -> World:
    return _world({ANA: "ana", BEN: "ben"})


@pytest.fixture
def recipes(world: World) -> FakeRecipes:
    return FakeRecipes(world)


def _copy(
    world: World,
    recipes: FakeRecipes,
    kitchen_id: UUID,
    source: UUID,
    *,
    actor: UUID = ANA,
    on_repeat: str = "ask",
    locks: FakeLocks | None = None,
    jobs: FakeEmbeddingJobs | None = None,
):
    service = CopyRecipeToKitchenService(
        world.kitchens,
        world.notebooks,
        recipes,
        world.catalog,
        world.prefs,
        locks or FakeLocks(),
        embedding_jobs=jobs,
    )
    return service.execute(
        CopyRecipeToKitchenCommand(
            actor_id=actor,
            kitchen_id=kitchen_id,
            source_recipe_id=source,
            on_repeat=on_repeat,  # type: ignore[arg-type]
        )
    )


def test_new_copy_goes_to_the_callers_own_kitchen_notebook(
    world: World, recipes: FakeRecipes
) -> None:
    kitchen = _kitchen(world, ANA)
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "lentils", "onion", "lentils")
    jobs = FakeEmbeddingJobs()

    copied = _copy(world, recipes, kitchen, source, jobs=jobs)

    notebook = world.notebooks.notebooks[copied.notebook_id]
    assert notebook.kitchen_id == kitchen
    assert notebook.owner_user_id == ANA
    assert copied.notebook_name == notebook.name
    assert copied.overwritten is False
    assert recipes.copies[copied.recipe_id] == (source, copied.notebook_id, ANA)
    assert {"lentils", "onion"} <= world.catalog.names[copied.notebook_id]
    assert jobs.enqueued == [copied.recipe_id]


def test_an_existing_own_kitchen_notebook_is_reused(world: World, recipes: FakeRecipes) -> None:
    kitchen = _kitchen(world, ANA)
    personal = _personal(world, ANA, "ana's Notebook")
    first = _copy(world, recipes, kitchen, recipes.add(personal, "rice"))
    second = _copy(world, recipes, kitchen, recipes.add(personal, "rice"))
    assert first.notebook_id == second.notebook_id


def test_non_member_and_missing_kitchen_are_not_found(world: World, recipes: FakeRecipes) -> None:
    kitchen = _kitchen(world, BEN)
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "rice")
    with pytest.raises(KitchenNotFoundError):
        _copy(world, recipes, kitchen, source)
    with pytest.raises(KitchenNotFoundError):
        _copy(world, recipes, uuid4(), source)


def test_archived_kitchen_refuses(world: World, recipes: FakeRecipes) -> None:
    kitchen = _kitchen(world, ANA, archived=True)
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "rice")
    with pytest.raises(KitchenArchivedError):
        _copy(world, recipes, kitchen, source)
    assert recipes.copies == {}


def test_unreadable_or_missing_source_is_not_found(
    world: World, recipes: FakeRecipes
) -> None:
    kitchen = _kitchen(world, ANA)
    _join(world, kitchen, BEN)
    bens = recipes.add(_personal(world, BEN, "ben's Notebook"), "rice")
    with pytest.raises(RecipeNotFoundError):
        _copy(world, recipes, kitchen, bens)
    with pytest.raises(RecipeNotFoundError):
        _copy(world, recipes, kitchen, uuid4())
    copied = _copy(world, recipes, kitchen, recipes.add(_personal(world, ANA, "a"), "x"))
    kitchen_recipe = recipes.add(copied.notebook_id, "x")
    # A kitchen notebook the caller can read is a valid source (spec 069, all notebooks).
    again = _copy(world, recipes, kitchen, kitchen_recipe, on_repeat="add")
    assert again.overwritten is False


def test_a_notebook_member_may_copy(world: World, recipes: FakeRecipes) -> None:
    kitchen = _kitchen(world, ANA)
    _join(world, kitchen, BEN)
    personal = _personal(world, ANA, "ana's Notebook")
    world.notebooks.roles[(personal, BEN)] = "member"
    copied = _copy(world, recipes, kitchen, recipes.add(personal, "rice"), actor=BEN)
    assert world.notebooks.notebooks[copied.notebook_id].owner_user_id == BEN


def test_repeat_asks_with_the_latest_copy(world: World, recipes: FakeRecipes) -> None:
    kitchen = _kitchen(world, ANA)
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "rice")
    _copy(world, recipes, kitchen, source)
    latest = _copy(world, recipes, kitchen, source, on_repeat="add")

    with pytest.raises(RecipeAlreadyInKitchenError) as raised:
        _copy(world, recipes, kitchen, source)

    assert raised.value.existing_recipe_id == latest.recipe_id
    assert raised.value.notebook_name == latest.notebook_name
    assert len(recipes.copies) == 2


def test_overwrite_replaces_the_latest_copy(world: World, recipes: FakeRecipes) -> None:
    kitchen = _kitchen(world, ANA)
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "rice")
    first = _copy(world, recipes, kitchen, source)
    jobs = FakeEmbeddingJobs()

    over = _copy(world, recipes, kitchen, source, on_repeat="overwrite", jobs=jobs)

    assert over.overwritten is True
    assert over.recipe_id == first.recipe_id
    assert recipes.overwrites == [(first.recipe_id, source, ANA)]
    assert jobs.enqueued == [first.recipe_id]
    assert len(recipes.copies) == 1


def test_overwrite_with_no_earlier_copy_makes_a_new_one(world: World, recipes: FakeRecipes) -> None:
    kitchen = _kitchen(world, ANA)
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "rice")
    copied = _copy(world, recipes, kitchen, source, on_repeat="overwrite")
    assert copied.overwritten is False
    assert recipes.overwrites == []


def test_overwrite_refused_while_the_copy_is_being_edited(
    world: World, recipes: FakeRecipes
) -> None:
    kitchen = _kitchen(world, ANA)
    source = recipes.add(_personal(world, ANA, "ana's Notebook"), "rice")
    first = _copy(world, recipes, kitchen, source)
    locks = FakeLocks({first.recipe_id: LockHolder(uuid4(), BEN, "ben", NOW)})
    with pytest.raises(RecipeLockedError):
        _copy(world, recipes, kitchen, source, on_repeat="overwrite", locks=locks)
    assert recipes.overwrites == []
