"""Save a confirmed draft against fake ports (spec 020 FR-002 to FR-013, FR-019)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from application.notebooks import CaptureNotebook
from application.ports import DuplicateSaveKeyError, NotebookFacts, StoredRecipe
from application.recipe_capture import TextTooLongError
from application.recipe_save import SaveRecipeCommand, SaveRecipeDraft
from domain.errors import (
    KitchenArchivedError,
    NotebookChoiceRequiredError,
    NotebookNotFoundError,
)
from domain.notebook import Notebook
from domain.recipe import NewRecipe
from domain.recipe_draft import DraftProblems, IngredientLine, InvalidDraftError

MAX_TEXT = 200


@dataclass
class FakeNotebooks:
    facts: dict[UUID, NotebookFacts] = field(default_factory=dict)

    def facts_for(self, user_id: UUID, notebook_id: UUID) -> NotebookFacts | None:
        return self.facts.get(notebook_id)


@dataclass
class FakeCatalog:
    names: dict[UUID, list[str]] = field(default_factory=dict)
    fail_add: bool = False

    def names_for_notebook(self, notebook_id: UUID) -> list[str]:
        return list(self.names.get(notebook_id, []))

    def add_names(self, notebook_id: UUID, names) -> None:
        if self.fail_add:
            raise RuntimeError("catalog down")
        current = self.names.setdefault(notebook_id, [])
        current.extend(n for n in names if n not in current)


@dataclass
class FakeRecipes:
    stored: list[NewRecipe] = field(default_factory=list)
    race_winner: StoredRecipe | None = None
    by_key: dict[tuple[UUID, UUID], StoredRecipe] = field(default_factory=dict)

    def find_by_save_key(self, author_id: UUID, save_key: UUID) -> StoredRecipe | None:
        return self.by_key.get((author_id, save_key))

    def add(self, recipe: NewRecipe) -> StoredRecipe:
        if self.race_winner is not None:
            self.by_key[(recipe.author_id, recipe.save_key)] = self.race_winner
            raise DuplicateSaveKeyError
        self.stored.append(recipe)
        row = StoredRecipe(id=uuid4(), notebook_id=recipe.notebook_id, title=recipe.title)
        self.by_key[(recipe.author_id, recipe.save_key)] = row
        return row


@dataclass
class FakeCaptureNotebook:
    result: CaptureNotebook | None = None
    error: Exception | None = None
    calls: int = 0

    def execute(self, command) -> CaptureNotebook:
        self.calls += 1
        if self.error:
            raise self.error
        assert self.result is not None
        return self.result


def personal(role: str = "owner") -> tuple[NotebookFacts, UUID]:
    notebook_id = uuid4()
    return (
        NotebookFacts(
            notebook=Notebook(id=notebook_id, name="ana's Notebook"),
            role=role,
            in_kitchen=False,
            owner_alias="ana",
            kitchen_is_archived=None,
            is_default=True,
        ),
        notebook_id,
    )


def kitchen(*, in_kitchen: bool = True, archived: bool = False) -> tuple[NotebookFacts, UUID]:
    notebook_id = uuid4()
    return (
        NotebookFacts(
            notebook=Notebook(id=notebook_id, name="Home notebook", kitchen_id=uuid4()),
            role=None,
            in_kitchen=in_kitchen,
            owner_alias="ana",
            kitchen_is_archived=archived,
            is_default=False,
        ),
        notebook_id,
    )


class Harness:
    def __init__(self) -> None:
        self.user_id = uuid4()
        self.notebooks = FakeNotebooks()
        self.catalog = FakeCatalog()
        self.recipes = FakeRecipes()
        self.capture_notebook = FakeCaptureNotebook()
        self.save = SaveRecipeDraft(
            self.notebooks,
            self.catalog,
            self.recipes,
            self.capture_notebook,  # type: ignore[arg-type]
            max_text_chars=MAX_TEXT,
        )

    def add(self, fact: NotebookFacts, names: list[str] | None = None) -> UUID:
        self.notebooks.facts[fact.notebook.id] = fact
        self.catalog.names[fact.notebook.id] = list(names or [])
        return fact.notebook.id

    def run(self, notebook_id: UUID | None, **overrides):
        values = {
            "actor_user_id": self.user_id,
            "save_key": uuid4(),
            "source_text": "2 large onions, chopped. Simmer them.",
            "title": "Onion soup",
            "base_servings": 4,
            "servings_estimated": False,
            "lines": (
                IngredientLine("onion", False, 2.0, "unit", "large", None, "chopped"),
                IngredientLine("salt", True, note="a pinch"),
            ),
            "steps": ("Simmer the onion.",),
            "notebook_id": notebook_id,
        }
        values.update(overrides)
        return self.save.execute(SaveRecipeCommand(**values))


def test_a_personal_notebook_gets_one_recipe_with_the_actor_as_author() -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact)
    saved = h.run(nid)
    assert saved.created and len(h.recipes.stored) == 1
    recipe = h.recipes.stored[0]
    assert recipe.author_id == h.user_id and recipe.notebook_id == nid
    assert recipe.source_text.startswith("2 large onions")


def test_a_kitchen_notebook_gets_the_recipe_and_nothing_else_is_written() -> None:
    h = Harness()
    fact, nid = kitchen()
    h.add(fact)
    h.run(nid)
    assert [r.notebook_id for r in h.recipes.stored] == [nid]
    assert set(h.catalog.names) == {nid}


def test_the_edited_values_are_stored_as_sent() -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact)
    h.run(
        nid,
        title="  Better soup ",
        servings_estimated=True,
        steps=("First.", "Second."),
    )
    recipe = h.recipes.stored[0]
    assert recipe.title == "Better soup" and recipe.servings_estimated is True
    assert recipe.steps == ("First.", "Second.")
    assert [line.name for line in recipe.lines] == ["onion", "salt"]
    assert recipe.lines[1].vague and recipe.lines[1].note == "a pinch"


def test_the_same_save_key_returns_the_first_recipe_and_adds_nothing() -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact)
    key = uuid4()
    first = h.run(nid, save_key=key)
    second = h.run(nid, save_key=key)
    assert first.created and not second.created
    assert second.recipe.id == first.recipe.id and len(h.recipes.stored) == 1
    assert second.created_catalog_names == ()


def test_a_duplicate_key_race_returns_the_stored_recipe() -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact)
    h.recipes.race_winner = StoredRecipe(id=uuid4(), notebook_id=nid, title="Winner")
    saved = h.run(nid)
    assert not saved.created and saved.recipe.title == "Winner"
    assert h.recipes.stored == [] and h.catalog.names[nid] == []


def test_new_names_join_the_catalog_and_matched_names_do_not() -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact, ["onion"])
    saved = h.run(
        nid,
        lines=(
            IngredientLine("Onion ", False, 1.0, "unit"),
            IngredientLine("leek", False, 1.0, "unit"),
            IngredientLine("leek", True, note="some"),
        ),
    )
    assert saved.created_catalog_names == ("leek",)
    assert h.catalog.names[nid] == ["onion", "leek"]
    assert [line.name for line in h.recipes.stored[0].lines] == ["onion", "leek", "leek"]


def test_an_undone_change_keeps_the_name_and_adds_it() -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact, ["onion"])
    h.run(nid, lines=(IngredientLine("onions", False, 2.0, "unit"),))
    assert h.catalog.names[nid] == ["onion", "onions"]


def test_an_empty_catalog_gets_every_distinct_name() -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact)
    h.run(nid)
    assert h.catalog.names[nid] == ["onion", "salt"]


def test_a_failed_catalog_write_propagates_so_the_request_rolls_back() -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact)
    h.catalog.fail_add = True
    with pytest.raises(RuntimeError):
        h.run(nid)


def test_an_archived_kitchen_refuses_and_stores_nothing() -> None:
    h = Harness()
    fact, nid = kitchen(archived=True)
    h.add(fact)
    with pytest.raises(KitchenArchivedError):
        h.run(nid)
    assert h.recipes.stored == [] and h.catalog.names[nid] == []


@pytest.mark.parametrize("make", [lambda: kitchen(in_kitchen=False), lambda: personal(None)])
def test_no_access_reads_as_a_missing_notebook(make) -> None:
    h = Harness()
    fact, nid = make()
    h.add(fact)
    with pytest.raises(NotebookNotFoundError):
        h.run(nid)
    with pytest.raises(NotebookNotFoundError):
        h.run(uuid4())
    assert h.recipes.stored == []


def test_a_kitchen_without_a_notebook_creates_one_through_the_capture_step() -> None:
    h = Harness()
    fact, nid = kitchen()
    h.add(fact)
    h.capture_notebook.result = CaptureNotebook(notebook_id=nid, created=True)
    saved = h.run(None, kitchen_id=uuid4())
    assert h.capture_notebook.calls == 1 and saved.recipe.notebook_id == nid


def test_a_notebook_the_draft_names_is_never_replaced_by_the_capture_step() -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact)
    h.run(nid)
    assert h.capture_notebook.calls == 0


def test_several_kitchen_notebooks_without_a_pick_is_refused() -> None:
    h = Harness()
    h.capture_notebook.error = NotebookChoiceRequiredError([uuid4(), uuid4()])
    with pytest.raises(NotebookChoiceRequiredError):
        h.run(None, kitchen_id=uuid4())
    assert h.recipes.stored == []


@pytest.mark.parametrize("ids", [(None, None), ("both", "both")])
def test_exactly_one_of_notebook_and_kitchen_is_required(ids) -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact)
    notebook_id = nid if ids[0] else None
    kitchen_id = uuid4() if ids[1] else None
    with pytest.raises(InvalidDraftError):
        h.run(notebook_id, kitchen_id=kitchen_id)


def test_a_broken_draft_stores_nothing() -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact)
    with pytest.raises(DraftProblems):
        h.run(nid, title=" ")
    with pytest.raises(InvalidDraftError):
        h.run(nid, lines=(IngredientLine("salt", True, quantity=1.0, note="x"),))
    assert h.recipes.stored == [] and h.catalog.names[nid] == []


def test_too_much_text_or_too_many_lines_or_steps_is_refused() -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact)
    with pytest.raises(TextTooLongError):
        h.run(nid, source_text="x" * (MAX_TEXT + 1))
    with pytest.raises(InvalidDraftError):
        h.run(nid, lines=tuple(IngredientLine(f"a{i}", True, note="x") for i in range(101)))
    with pytest.raises(InvalidDraftError):
        h.run(nid, steps=tuple(f"step {i}" for i in range(101)))
    assert h.recipes.stored == []


def test_the_log_never_holds_the_title_or_names(caplog: pytest.LogCaptureFixture) -> None:
    h = Harness()
    fact, nid = personal()
    h.add(fact)
    with caplog.at_level("INFO"):
        h.run(nid, title="Secret soup")
    text = caplog.text
    assert "Secret soup" not in text and "onion" not in text
