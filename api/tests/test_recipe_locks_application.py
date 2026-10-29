"""Recipe edit lock against fake ports (spec 022 US4)."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from application.ports import SessionRef
from application.recipe_locks import AcquireRecipeLockService, ReleaseRecipeLockService
from application.recipe_manage import (
    DeleteRecipeCommand,
    DeleteRecipeService,
    GetRecipeCommand,
    GetRecipeService,
    UpdateRecipeService,
)
from domain.errors import NotEditingError, RecipeLockedError, RecipeReadOnlyError
from tests.test_carts_application import FakeCartRepo, FakeLocks
from tests.test_notebooks_application import _join, _kitchen, _kitchen_notebook
from tests.test_recipe_manage_application import ANA, BEN, CAT, _setup, _update


def _world():  # noqa: ANN202
    world, recipes, catalog = _setup()
    kitchen = _kitchen(world, ANA)
    _join(world, kitchen, BEN)
    notebook = _kitchen_notebook(world, kitchen, "Home notebook", ANA)
    recipe_id = recipes.put(notebook)
    locks = FakeLocks(world, FakeCartRepo(world))
    return world, recipes, catalog, locks, kitchen, recipe_id


def test_one_holder_and_save_releases() -> None:
    world, recipes, catalog, locks, _, recipe_id = _world()
    ana, ben = SessionRef(ANA, uuid4()), SessionRef(BEN, uuid4())
    acquire = AcquireRecipeLockService(recipes, world.notebooks, locks)
    editor = acquire.execute(ana, recipe_id)
    assert editor.is_me and editor.alias == "ana" and editor.idle_expires_at is not None
    acquire.execute(ana, recipe_id)  # same session: keep-alive
    with pytest.raises(RecipeLockedError) as info:
        acquire.execute(ben, recipe_id)
    assert info.value.editor_alias == "ana"

    get = GetRecipeService(recipes, world.notebooks, locks)
    seen = get.execute(GetRecipeCommand(BEN, recipe_id, ben))
    assert seen.editor is not None and not seen.editor.is_me

    update = UpdateRecipeService(recipes, world.notebooks, catalog, locks)
    with pytest.raises(RecipeLockedError):
        update.execute(_update(recipes, recipe_id, BEN, session_id=ben.session_id))
    with pytest.raises(RecipeLockedError):
        DeleteRecipeService(recipes, world.notebooks, locks).execute(
            DeleteRecipeCommand(BEN, recipe_id, ben.session_id)
        )
    update.execute(_update(recipes, recipe_id, ANA, title="New", session_id=ana.session_id))
    assert locks.recipe_locks == {}
    acquire.execute(ben, recipe_id)


def test_update_without_lock_is_not_editing() -> None:
    world, recipes, catalog, locks, _, recipe_id = _world()
    update = UpdateRecipeService(recipes, world.notebooks, catalog, locks)
    with pytest.raises(NotEditingError):
        update.execute(_update(recipes, recipe_id, ANA, session_id=uuid4()))
    assert recipes.writes == []


def test_dead_session_idle_and_lost_write_free_the_lock() -> None:
    world, recipes, catalog, locks, _, recipe_id = _world()
    ana, ben = SessionRef(ANA, uuid4()), SessionRef(BEN, uuid4())
    acquire = AcquireRecipeLockService(recipes, world.notebooks, locks)
    acquire.execute(ana, recipe_id)
    locks.dead_sessions.add(ana.session_id)
    acquire.execute(ben, recipe_id)
    UpdateRecipeService(recipes, world.notebooks, catalog, locks).execute(
        _update(recipes, recipe_id, BEN, session_id=ben.session_id)
    )

    ana2 = SessionRef(ANA, uuid4())
    acquire.execute(ana2, recipe_id)
    locks.clock.advance(timedelta(minutes=4))
    acquire.execute(ana2, recipe_id)  # keep-alive
    locks.clock.advance(timedelta(minutes=4))
    with pytest.raises(RecipeLockedError):
        acquire.execute(ben, recipe_id)
    locks.clock.advance(timedelta(minutes=1))
    acquire.execute(ben, recipe_id)
    with pytest.raises(RecipeLockedError):
        UpdateRecipeService(recipes, world.notebooks, catalog, locks).execute(
            _update(recipes, recipe_id, ANA, session_id=ana2.session_id)
        )

    locks.no_write.add((recipe_id, BEN))  # Ben lost write access
    acquire.execute(ana2, recipe_id)


def test_reader_without_write_cannot_lock_and_release_is_idempotent() -> None:
    world, recipes, _, locks, _, recipe_id = _world()
    cat = SessionRef(CAT, uuid4())
    kitchen = _kitchen(world, ANA, "Archived", archived=True)
    _join(world, kitchen, CAT)
    archived_recipe = recipes.put(_kitchen_notebook(world, kitchen, "Old", ANA))
    acquire = AcquireRecipeLockService(recipes, world.notebooks, locks)
    with pytest.raises(RecipeReadOnlyError):
        acquire.execute(cat, archived_recipe)
    release = ReleaseRecipeLockService(locks)
    release.execute(cat, recipe_id)
    release.execute(cat, recipe_id)
