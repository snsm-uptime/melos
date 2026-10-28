"""Recipe detail, edit and delete use cases against fake ports (spec 027)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from application.ports import RecipeDetail, RecipeLineDetail
from application.recipe_manage import (
    DeleteRecipeCommand,
    DeleteRecipeService,
    GetRecipeCommand,
    GetRecipeService,
    MatchRecipeNamesCommand,
    MatchRecipeNamesService,
    UpdateRecipeCommand,
    UpdateRecipeService,
    _recipe_for,
)
from domain.errors import RecipeChangedError, RecipeNotFoundError, RecipeReadOnlyError
from domain.recipe import EditedRecipe
from domain.recipe_draft import DraftProblems, IngredientLine, InvalidDraftError
from tests.test_notebooks_application import (
    World,
    _join,
    _kitchen,
    _kitchen_notebook,
    _personal,
    _world,
)

START = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)


@dataclass
class FakeRecipes:
    """Recipes in memory, with a monotonic clock for `updated_at` and a log of writes."""

    recipes: dict[UUID, RecipeDetail] = field(default_factory=dict)
    sources: set[UUID] = field(default_factory=set)
    writes: list[str] = field(default_factory=list)
    _tick: int = 0

    def _now(self) -> datetime:
        self._tick += 1
        return START + timedelta(seconds=self._tick)

    def put(
        self,
        notebook_id: UUID,
        title: str = "Tomato rice",
        *,
        lines: tuple[RecipeLineDetail, ...] | None = None,
        steps: tuple[str, ...] = ("Fry the garlic.", "Add the rice."),
        author_alias: str | None = "ana",
    ) -> UUID:
        recipe_id = uuid4()
        now = self._now()
        self.recipes[recipe_id] = RecipeDetail(
            id=recipe_id,
            notebook_id=notebook_id,
            title=title,
            base_servings=4,
            servings_estimated=False,
            author_alias=author_alias,
            lines=lines
            if lines is not None
            else (RecipeLineDetail("rice", False, 1.0, "cup", None, None, None),),
            steps=steps,
            source_type="text",
            source_url=None,
            created_at=now,
            updated_at=now,
        )
        self.sources.add(recipe_id)
        return recipe_id

    # RecipeRepository
    def get_detail(self, recipe_id: UUID) -> RecipeDetail | None:
        return self.recipes.get(recipe_id)

    def replace(self, recipe_id: UUID, version: datetime, recipe: EditedRecipe) -> RecipeDetail:
        current = self.recipes.get(recipe_id)
        if current is None:
            raise RecipeNotFoundError()
        if current.updated_at != version:
            raise RecipeChangedError()
        self.writes.append("replace")
        updated = replace(
            current,
            title=recipe.title,
            base_servings=recipe.base_servings,
            servings_estimated=recipe.servings_estimated,
            lines=tuple(
                RecipeLineDetail(
                    name=line.name,
                    vague=line.vague,
                    quantity=None if line.vague else line.quantity,
                    unit=None if line.vague else line.unit,
                    size=None if line.vague else line.size,
                    preparation=line.preparation,
                    note=line.note if line.vague else None,
                )
                for line in recipe.lines
            ),
            steps=recipe.steps,
            updated_at=self._now(),
        )
        self.recipes[recipe_id] = updated
        return updated

    def delete(self, recipe_id: UUID) -> None:
        if recipe_id not in self.recipes:
            raise RecipeNotFoundError()
        self.writes.append("delete")
        del self.recipes[recipe_id]
        self.sources.discard(recipe_id)


@dataclass
class FakeCatalog:
    """The world's notebook catalog plus `add_names`, with a log of what was added."""

    world: World
    added: list[tuple[UUID, tuple[str, ...]]] = field(default_factory=list)

    def names_for_notebook(self, notebook_id: UUID) -> list[str]:
        return self.world.catalog.names_for_notebook(notebook_id)

    def add_names(self, notebook_id: UUID, names: tuple[str, ...] | list[str]) -> None:
        self.added.append((notebook_id, tuple(names)))
        self.world.catalog.names.setdefault(notebook_id, set()).update(names)


ANA, BEN, CAT = uuid4(), uuid4(), uuid4()


def _setup() -> tuple[World, FakeRecipes, FakeCatalog]:
    world = _world({ANA: "ana", BEN: "ben", CAT: "cat"})
    return world, FakeRecipes(), FakeCatalog(world)


def _line(name: str = "rice", **kw: object) -> IngredientLine:
    base: dict[str, object] = {"name": name, "vague": False, "quantity": 1.0, "unit": "cup"}
    base.update(kw)
    return IngredientLine(**base)  # type: ignore[arg-type]


def _update(
    recipes: FakeRecipes, recipe_id: UUID, actor: UUID, **overrides: object
) -> UpdateRecipeCommand:
    current = recipes.recipes[recipe_id]
    fields: dict[str, object] = {
        "actor_user_id": actor,
        "recipe_id": recipe_id,
        "version": current.updated_at,
        "title": current.title,
        "base_servings": current.base_servings,
        "servings_estimated": False,
        "lines": (_line(),),
        "steps": ("Fry the garlic.",),
    }
    fields.update(overrides)
    return UpdateRecipeCommand(**fields)  # type: ignore[arg-type]


# --- access (_recipe_for) -------------------------------------------------------------------


def test_missing_recipe_and_non_reader_get_the_same_not_found() -> None:
    world, recipes, _ = _setup()
    nb = _personal(world, ANA, "ana's Notebook")
    recipe_id = recipes.put(nb)
    for actor, rid in [(ANA, uuid4()), (BEN, recipe_id)]:
        with pytest.raises(RecipeNotFoundError) as caught:
            _recipe_for(recipes, world.notebooks, actor, rid, write=False)
        assert str(caught.value) == RecipeNotFoundError.MESSAGE


def test_recipe_in_an_unknown_notebook_is_not_found() -> None:
    world, recipes, _ = _setup()
    recipe_id = recipes.put(uuid4())
    with pytest.raises(RecipeNotFoundError):
        _recipe_for(recipes, world.notebooks, ANA, recipe_id, write=False)


def test_personal_member_and_kitchen_member_may_write() -> None:
    world, recipes, _ = _setup()
    personal = _personal(world, ANA, "ana's Notebook")
    world.notebooks.roles[(personal, BEN)] = "member"
    kitchen = _kitchen(world, ANA)
    _join(world, kitchen, BEN)
    shared = _kitchen_notebook(world, kitchen, "Home notebook", ANA)
    own = recipes.put(personal)
    theirs = recipes.put(shared)
    assert _recipe_for(recipes, world.notebooks, BEN, own, write=True).can_write
    assert _recipe_for(recipes, world.notebooks, BEN, theirs, write=True).can_write


def test_archived_kitchen_member_reads_but_cannot_write() -> None:
    world, recipes, _ = _setup()
    kitchen = _kitchen(world, ANA, archived=True)
    _join(world, kitchen, BEN)
    shared = _kitchen_notebook(world, kitchen, "Home notebook", ANA)
    recipe_id = recipes.put(shared)
    view = _recipe_for(recipes, world.notebooks, BEN, recipe_id, write=False)
    assert view.can_write is False
    with pytest.raises(RecipeReadOnlyError):
        _recipe_for(recipes, world.notebooks, BEN, recipe_id, write=True)


# --- read (US1) -----------------------------------------------------------------------------


def test_get_returns_lines_and_steps_as_saved_and_writes_nothing() -> None:
    world, recipes, _ = _setup()
    nb = _personal(world, ANA, "ana's Notebook")
    lines = (
        RecipeLineDetail("rice", False, 1.0, "cup", None, None, None),
        RecipeLineDetail("onion", False, 2.0, "unit", "large", "chopped", None),
        RecipeLineDetail("salt", True, None, None, None, None, "to taste"),
    )
    recipe_id = recipes.put(nb, lines=lines, steps=("one", "two", "three"))
    view = GetRecipeService(recipes, world.notebooks).execute(GetRecipeCommand(ANA, recipe_id))
    assert view.detail.lines == lines
    assert view.detail.steps == ("one", "two", "three")
    assert view.can_write is True
    assert view.notebook.id == nb
    assert recipes.writes == []


def test_get_with_a_gone_author_has_no_alias() -> None:
    world, recipes, _ = _setup()
    nb = _personal(world, ANA, "ana's Notebook")
    recipe_id = recipes.put(nb, author_alias=None)
    view = GetRecipeService(recipes, world.notebooks).execute(GetRecipeCommand(ANA, recipe_id))
    assert view.detail.author_alias is None


# --- name matches ---------------------------------------------------------------------------


def test_name_matches_propose_catalog_entries() -> None:
    world, recipes, catalog = _setup()
    nb = _personal(world, ANA, "ana's Notebook", {"onion", "rice"})
    recipe_id = recipes.put(nb)
    result = MatchRecipeNamesService(recipes, world.notebooks, catalog).execute(
        MatchRecipeNamesCommand(ANA, recipe_id, ("onions", "garlic"))
    )
    assert result == [("onions", "onion"), ("garlic", None)]
    assert catalog.added == []


def test_name_matches_need_write_access() -> None:
    world, recipes, catalog = _setup()
    kitchen = _kitchen(world, ANA, archived=True)
    shared = _kitchen_notebook(world, kitchen, "Home notebook", ANA)
    recipe_id = recipes.put(shared)
    with pytest.raises(RecipeReadOnlyError):
        MatchRecipeNamesService(recipes, world.notebooks, catalog).execute(
            MatchRecipeNamesCommand(ANA, recipe_id, ("onions",))
        )


# --- edit (US2) -----------------------------------------------------------------------------


def _update_service(
    world: World, recipes: FakeRecipes, catalog: FakeCatalog
) -> UpdateRecipeService:
    return UpdateRecipeService(recipes, world.notebooks, catalog)


def test_edit_changes_content_and_keeps_order_and_author() -> None:
    world, recipes, catalog = _setup()
    kitchen = _kitchen(world, ANA)
    _join(world, kitchen, BEN)
    shared = _kitchen_notebook(world, kitchen, "Home notebook", ANA)
    recipe_id = recipes.put(shared, author_alias="ana")
    before = recipes.recipes[recipe_id]
    command = _update(
        recipes,
        recipe_id,
        BEN,
        title="Better rice",
        lines=(_line(quantity=2.0), _line("onion", quantity=1.0, unit="unit")),
        steps=("first", "second"),
    )
    result = _update_service(world, recipes, catalog).execute(command)
    after = result.view.detail
    assert after.title == "Better rice"
    assert [line.name for line in after.lines] == ["rice", "onion"]
    assert after.lines[0].quantity == 2.0
    assert after.steps == ("first", "second")
    assert after.author_alias == before.author_alias
    assert after.notebook_id == before.notebook_id
    assert after.created_at == before.created_at
    assert after.updated_at > before.updated_at


def test_edit_adds_new_names_and_resolves_spelling() -> None:
    world, recipes, catalog = _setup()
    nb = _personal(world, ANA, "ana's Notebook", {"onion", "rice"})
    recipe_id = recipes.put(nb)
    command = _update(recipes, recipe_id, ANA, lines=(_line(" Onion "), _line("garlic")))
    result = _update_service(world, recipes, catalog).execute(command)
    assert [line.name for line in result.view.detail.lines] == ["onion", "garlic"]
    assert result.created_catalog_names == ("garlic",)
    assert catalog.added == [(nb, ("garlic",))]
    assert world.catalog.names[nb] == {"onion", "rice", "garlic"}


def test_edit_never_removes_catalog_names() -> None:
    world, recipes, catalog = _setup()
    nb = _personal(world, ANA, "ana's Notebook", {"onion", "rice"})
    recipe_id = recipes.put(nb)
    _update_service(world, recipes, catalog).execute(
        _update(recipes, recipe_id, ANA, lines=(_line("tomato"),))
    )
    assert {"onion", "rice"} <= world.catalog.names[nb]


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": "   "},
        {"steps": ()},
        {"steps": ("  ",)},
        {"lines": ()},
        {"lines": (_line(unit=None),)},
        {"lines": (_line(quantity=None),)},
        {"lines": (_line(quantity=0.0),)},
        {"base_servings": 0},
        {"lines": (IngredientLine(name="salt", vague=True, quantity=2.0, unit="g", note="x"),)},
        {"lines": tuple(_line(f"item{n}") for n in range(101))},
    ],
)
def test_edit_breaking_a_rule_stores_nothing(overrides: dict[str, object]) -> None:
    world, recipes, catalog = _setup()
    nb = _personal(world, ANA, "ana's Notebook")
    recipe_id = recipes.put(nb)
    before = recipes.recipes[recipe_id]
    with pytest.raises((DraftProblems, InvalidDraftError)):
        _update_service(world, recipes, catalog).execute(
            _update(recipes, recipe_id, ANA, **overrides)
        )
    assert recipes.recipes[recipe_id] == before
    assert recipes.writes == []
    assert catalog.added == []


def test_edit_without_ingredient_lines_names_the_missing_part() -> None:
    world, recipes, catalog = _setup()
    nb = _personal(world, ANA, "ana's Notebook")
    recipe_id = recipes.put(nb)
    with pytest.raises(DraftProblems) as caught:
        _update_service(world, recipes, catalog).execute(
            _update(recipes, recipe_id, ANA, lines=(), title="")
        )
    assert set(caught.value.missing) == {"title", "ingredients"}


def test_edit_by_a_read_only_member_is_refused() -> None:
    world, recipes, catalog = _setup()
    kitchen = _kitchen(world, ANA, archived=True)
    shared = _kitchen_notebook(world, kitchen, "Home notebook", ANA)
    recipe_id = recipes.put(shared)
    with pytest.raises(RecipeReadOnlyError):
        _update_service(world, recipes, catalog).execute(_update(recipes, recipe_id, ANA))
    assert recipes.writes == []


def test_edit_by_a_non_reader_or_of_a_gone_recipe_is_not_found() -> None:
    world, recipes, catalog = _setup()
    nb = _personal(world, ANA, "ana's Notebook")
    recipe_id = recipes.put(nb)
    command = _update(recipes, recipe_id, BEN)
    with pytest.raises(RecipeNotFoundError):
        _update_service(world, recipes, catalog).execute(command)
    del recipes.recipes[recipe_id]
    with pytest.raises(RecipeNotFoundError):
        _update_service(world, recipes, catalog).execute(command)


def test_stale_edit_is_refused_and_stores_nothing() -> None:
    world, recipes, catalog = _setup()
    nb = _personal(world, ANA, "ana's Notebook")
    recipe_id = recipes.put(nb)
    stale = _update(recipes, recipe_id, ANA, title="First")
    _update_service(world, recipes, catalog).execute(stale)
    catalog.added.clear()
    with pytest.raises(RecipeChangedError):
        _update_service(world, recipes, catalog).execute(
            replace(stale, title="Second", lines=(_line("garlic"),))
        )
    assert recipes.recipes[recipe_id].title == "First"
    assert catalog.added == []


# --- delete (US3) ---------------------------------------------------------------------------


def test_delete_removes_the_recipe_and_its_source() -> None:
    world, recipes, _ = _setup()
    personal = _personal(world, ANA, "ana's Notebook")
    world.notebooks.roles[(personal, BEN)] = "member"
    kitchen = _kitchen(world, CAT)
    shared = _kitchen_notebook(world, kitchen, "Home notebook", CAT)
    service = DeleteRecipeService(recipes, world.notebooks)
    for actor, notebook in [(ANA, personal), (BEN, personal), (CAT, shared)]:
        recipe_id = recipes.put(notebook)
        service.execute(DeleteRecipeCommand(actor, recipe_id))
        assert recipe_id not in recipes.recipes
        assert recipe_id not in recipes.sources


def test_delete_leaves_other_recipes_and_copies_alone() -> None:
    world, recipes, _ = _setup()
    original_nb = _personal(world, ANA, "ana's Notebook")
    copy_nb = _personal(world, BEN, "ben's Notebook")
    original = recipes.put(original_nb)
    sibling = recipes.put(original_nb, "Soup")
    copy = recipes.put(copy_nb)
    sibling_before, copy_before = recipes.recipes[sibling], recipes.recipes[copy]
    DeleteRecipeService(recipes, world.notebooks).execute(DeleteRecipeCommand(ANA, original))
    assert recipes.recipes[sibling] == sibling_before
    assert recipes.recipes[copy] == copy_before


def test_delete_by_read_only_member_or_non_reader_removes_nothing() -> None:
    world, recipes, _ = _setup()
    kitchen = _kitchen(world, ANA, archived=True)
    shared = _kitchen_notebook(world, kitchen, "Home notebook", ANA)
    mine = _personal(world, BEN, "ben's Notebook")
    archived_recipe, private_recipe = recipes.put(shared), recipes.put(mine)
    service = DeleteRecipeService(recipes, world.notebooks)
    with pytest.raises(RecipeReadOnlyError):
        service.execute(DeleteRecipeCommand(ANA, archived_recipe))
    with pytest.raises(RecipeNotFoundError):
        service.execute(DeleteRecipeCommand(ANA, private_recipe))
    assert {archived_recipe, private_recipe} <= set(recipes.recipes)
    assert recipes.writes == []


def test_second_delete_is_not_found() -> None:
    world, recipes, _ = _setup()
    nb = _personal(world, ANA, "ana's Notebook")
    recipe_id = recipes.put(nb)
    service = DeleteRecipeService(recipes, world.notebooks)
    service.execute(DeleteRecipeCommand(ANA, recipe_id))
    with pytest.raises(RecipeNotFoundError):
        service.execute(DeleteRecipeCommand(ANA, recipe_id))
