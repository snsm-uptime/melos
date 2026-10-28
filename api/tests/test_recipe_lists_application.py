"""Recipe list use cases against fake ports (spec 021 FR-001 to FR-012)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from application.ports import RecipeCardRow, RecipePage
from application.recipe_lists import (
    ListKitchenRecipesCommand,
    ListKitchenRecipesService,
    ListNotebookRecipesCommand,
    ListNotebookRecipesService,
)
from domain.errors import InvalidPageError, KitchenNotFoundError, NotebookNotFoundError
from tests.test_notebooks_application import (
    World,
    _join,
    _kitchen,
    _kitchen_notebook,
    _personal,
    _world,
)

START = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


@dataclass
class FakeRecipeLists:
    """Cards per notebook; filters by title like the real key (already normalized)."""

    cards: list[RecipeCardRow] = field(default_factory=list)
    calls: list[tuple[tuple[UUID, ...], str, int, int]] = field(default_factory=list)

    def add(self, notebook_id: UUID, title: str, minutes: int) -> None:
        self.cards.append(
            RecipeCardRow(
                id=uuid4(),
                title=title,
                author_alias="ana",
                ingredient_count=3,
                notebook_id=notebook_id,
                notebook_name="n",
                created_at=START + timedelta(minutes=minutes),
            )
        )

    def list_page(
        self, notebook_ids: Sequence[UUID], key: str, offset: int, limit: int
    ) -> RecipePage:
        self.calls.append((tuple(notebook_ids), key, offset, limit))
        found = [
            card
            for card in sorted(self.cards, key=lambda c: c.created_at, reverse=True)
            if card.notebook_id in notebook_ids and key in card.title.lower()
        ]
        return RecipePage(items=found[offset : offset + limit], total=len(found))


def _notebook_service(world: World, lists: FakeRecipeLists) -> ListNotebookRecipesService:
    return ListNotebookRecipesService(world.notebooks, lists)


def _kitchen_service(world: World, lists: FakeRecipeLists) -> ListKitchenRecipesService:
    return ListKitchenRecipesService(world.kitchens, world.notebooks, lists)


def test_reader_sees_the_notebooks_recipes_newest_first() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    notebook = _personal(world, ana, "ana's Notebook")
    lists = FakeRecipeLists()
    lists.add(notebook, "Old soup", 1)
    lists.add(notebook, "New soup", 2)

    result = _notebook_service(world, lists).execute(
        ListNotebookRecipesCommand(actor_user_id=ana, notebook_id=notebook)
    )

    assert [card.title for card in result.items] == ["New soup", "Old soup"]
    assert (result.page, result.total, result.total_pages, result.page_size) == (1, 2, 1, 12)


def test_stranger_and_missing_notebook_get_the_same_not_found() -> None:
    ana, carl = uuid4(), uuid4()
    world = _world({ana: "ana", carl: "carl"})
    notebook = _personal(world, ana, "ana's Notebook")
    lists = FakeRecipeLists()

    with pytest.raises(NotebookNotFoundError):
        _notebook_service(world, lists).execute(
            ListNotebookRecipesCommand(actor_user_id=carl, notebook_id=notebook)
        )
    with pytest.raises(NotebookNotFoundError):
        _notebook_service(world, lists).execute(
            ListNotebookRecipesCommand(actor_user_id=ana, notebook_id=uuid4())
        )
    assert lists.calls == []


def test_empty_notebook_is_page_one_of_one() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    notebook = _personal(world, ana, "ana's Notebook")

    result = _notebook_service(world, FakeRecipeLists()).execute(
        ListNotebookRecipesCommand(actor_user_id=ana, notebook_id=notebook)
    )

    assert (result.items, result.page, result.total, result.total_pages) == ([], 1, 0, 1)


def test_page_past_the_end_returns_the_last_page() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    notebook = _personal(world, ana, "ana's Notebook")
    lists = FakeRecipeLists()
    for index in range(13):
        lists.add(notebook, f"Recipe {index}", index)

    result = _notebook_service(world, lists).execute(
        ListNotebookRecipesCommand(actor_user_id=ana, notebook_id=notebook, page=9)
    )

    assert (result.page, result.total_pages, len(result.items)) == (2, 2, 1)


def test_page_below_one_is_invalid_and_reads_nothing() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    notebook = _personal(world, ana, "ana's Notebook")
    lists = FakeRecipeLists()

    with pytest.raises(InvalidPageError):
        _notebook_service(world, lists).execute(
            ListNotebookRecipesCommand(actor_user_id=ana, notebook_id=notebook, page=0)
        )
    assert lists.calls == []


def test_filter_text_reaches_the_repository_as_a_search_key() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    notebook = _personal(world, ana, "ana's Notebook")
    lists = FakeRecipeLists()

    _notebook_service(world, lists).execute(
        ListNotebookRecipesCommand(actor_user_id=ana, notebook_id=notebook, q="  Calabazá ")
    )

    assert lists.calls[0][1] == "calabaza"


def test_spaces_only_filter_behaves_as_no_filter() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    notebook = _personal(world, ana, "ana's Notebook")
    lists = FakeRecipeLists()
    lists.add(notebook, "Soup", 1)

    result = _notebook_service(world, lists).execute(
        ListNotebookRecipesCommand(actor_user_id=ana, notebook_id=notebook, q="   ")
    )

    assert lists.calls[0][1] == ""
    assert result.total == 1


def test_kitchen_list_merges_its_notebooks_and_never_a_personal_one() -> None:
    ana, ben = uuid4(), uuid4()
    world = _world({ana: "ana", ben: "ben"})
    home = _kitchen(world, ana)
    _join(world, home, ben)
    first = _kitchen_notebook(world, home, "ana's (Home) Notebook", ana)
    second = _kitchen_notebook(world, home, "Extra", ana)
    personal = _personal(world, ben, "ben's Notebook")
    lists = FakeRecipeLists()
    lists.add(first, "From first", 1)
    lists.add(second, "From second", 2)
    lists.add(personal, "Personal", 3)

    result = _kitchen_service(world, lists).execute(
        ListKitchenRecipesCommand(actor_user_id=ben, kitchen_id=home)
    )

    assert [card.title for card in result.items] == ["From second", "From first"]


def test_kitchen_non_member_and_missing_kitchen_get_the_same_not_found() -> None:
    ana, carl = uuid4(), uuid4()
    world = _world({ana: "ana", carl: "carl"})
    home = _kitchen(world, ana)

    with pytest.raises(KitchenNotFoundError):
        _kitchen_service(world, FakeRecipeLists()).execute(
            ListKitchenRecipesCommand(actor_user_id=carl, kitchen_id=home)
        )
    with pytest.raises(KitchenNotFoundError):
        _kitchen_service(world, FakeRecipeLists()).execute(
            ListKitchenRecipesCommand(actor_user_id=ana, kitchen_id=uuid4())
        )


def test_kitchen_without_notebook_is_empty_and_creates_nothing() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    home = _kitchen(world, ana)

    result = _kitchen_service(world, FakeRecipeLists()).execute(
        ListKitchenRecipesCommand(actor_user_id=ana, kitchen_id=home)
    )

    assert (result.items, result.total, result.page) == ([], 0, 1)
    assert "create" not in world.notebooks.calls
    assert "lock_kitchen" not in world.notebooks.calls


def test_archived_kitchen_still_lists() -> None:
    ana = uuid4()
    world = _world({ana: "ana"})
    home = _kitchen(world, ana, archived=True)
    notebook = _kitchen_notebook(world, home, "ana's (Home) Notebook", ana)
    lists = FakeRecipeLists()
    lists.add(notebook, "Soup", 1)

    result = _kitchen_service(world, lists).execute(
        ListKitchenRecipesCommand(actor_user_id=ana, kitchen_id=home)
    )

    assert result.total == 1
