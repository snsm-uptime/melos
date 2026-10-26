"""Recipe capture use case against fake ports (spec 016 FR-001a, FR-002, FR-019, FR-022, FR-033)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from adapters.llm.fake_extractor import FakeRecipeExtractor
from adapters.llm.vocabulary import load_vocabulary
from application.notebooks import NotebookView
from application.ports import NotebookFacts
from application.recipe_capture import (
    CapturedDraft,
    CaptureRecipeCommand,
    CaptureRecipeText,
    TextEmptyError,
    TextTooLongError,
)
from application.recipe_extraction import (
    AIProviderError,
    Draft,
    LimitReached,
    NotARecipe,
    NotRecipeReason,
    RecipeExtraction,
    Unavailable,
)
from domain.errors import KitchenArchivedError, NotebookNotFoundError
from domain.notebook import Notebook
from domain.recipe_draft import DraftRecipe, IngredientLine

VOCABULARY = load_vocabulary()
MAX_CHARS = 50
TEXT = "2 large onions, chopped. Simmer them."


def good_draft() -> DraftRecipe:
    return DraftRecipe(
        title="Onion soup",
        base_servings=4,
        servings_estimated=False,
        main_ingredients=(),
        cuisines=(),
        ingredient_lines=(IngredientLine("onion", False, 2.0, "unit", "large", None, "chopped"),),
        steps=("Simmer the onion.",),
    )


@dataclass
class FakeNotebooks:
    """Notebook facts by notebook id. A missing id or no facts for the caller reads as absent."""

    facts: dict[UUID, NotebookFacts] = field(default_factory=dict)
    reads: list[UUID] = field(default_factory=list)

    def get(self, notebook_id: UUID) -> Notebook | None:
        fact = self.facts.get(notebook_id)
        return fact.notebook if fact else None

    def facts_for(self, user_id: UUID, notebook_id: UUID) -> NotebookFacts | None:
        self.reads.append(notebook_id)
        return self.facts.get(notebook_id)


@dataclass
class FakeCatalog:
    names: dict[UUID, list[str]] = field(default_factory=dict)
    reads: list[UUID] = field(default_factory=list)

    def names_for_notebook(self, notebook_id: UUID) -> list[str]:
        self.reads.append(notebook_id)
        return self.names.get(notebook_id, [])


def personal_facts(user_id: UUID, *, role: str = "owner") -> tuple[NotebookFacts, UUID]:
    notebook_id = uuid4()
    fact = NotebookFacts(
        notebook=Notebook(id=notebook_id, name="ana's Notebook"),
        role=role,
        in_kitchen=False,
        owner_alias="ana",
        kitchen_is_archived=None,
        is_default=True,
    )
    return fact, notebook_id


def kitchen_facts(*, in_kitchen: bool = True, archived: bool = False) -> tuple[NotebookFacts, UUID]:
    notebook_id = uuid4()
    fact = NotebookFacts(
        notebook=Notebook(id=notebook_id, name="ana's (Home) Notebook", kitchen_id=uuid4()),
        role=None,
        in_kitchen=in_kitchen,
        owner_alias="ana",
        kitchen_is_archived=archived,
        is_default=False,
    )
    return fact, notebook_id


class Harness:
    def __init__(self, script, *, names: list[str] | None = None) -> None:
        self.user_id = uuid4()
        self.extractor = FakeRecipeExtractor(script=script)
        self.notebooks = FakeNotebooks()
        self.catalog = FakeCatalog()
        self.extraction = RecipeExtraction(self.extractor, VOCABULARY)
        self.capture = CaptureRecipeText(
            self.notebooks,
            self.catalog,
            self.extraction,
            max_chars=MAX_CHARS,
            timeout_s=10.0,
        )
        self.names = names or []

    def add(self, fact: NotebookFacts, notebook_id: UUID) -> UUID:
        self.notebooks.facts[notebook_id] = fact
        self.catalog.names[notebook_id] = self.names
        return notebook_id

    def run(self, notebook_id: UUID, text: str = TEXT):
        return self.capture.execute(
            CaptureRecipeCommand(
                actor_user_id=self.user_id,
                notebook_id=notebook_id,
                text=text,
                language="es",
            )
        )


def test_draft_is_returned_for_the_notebook_with_the_members_language() -> None:
    h = Harness(Draft(recipe=good_draft()))
    fact, notebook_id = personal_facts(uuid4())
    h.add(fact, notebook_id)

    outcome = h.run(notebook_id)

    assert isinstance(outcome, CapturedDraft)
    assert outcome.language == "es"
    assert isinstance(outcome.notebook, NotebookView)
    assert outcome.notebook.id == notebook_id
    assert outcome.recipe.title == "Onion soup"


def test_only_the_capture_notebooks_catalog_is_sent_to_the_assistant() -> None:
    h = Harness(Draft(recipe=good_draft()), names=["onion"])
    fact, notebook_id = personal_facts(uuid4())
    h.add(fact, notebook_id)
    other_fact, other_id = personal_facts(uuid4())
    h.notebooks.facts[other_id] = other_fact
    h.catalog.names[other_id] = ["flour", "salt"]

    h.run(notebook_id)

    assert h.catalog.reads == [notebook_id]
    assert h.extractor.calls[0].ingredient_names == ("onion",)


@pytest.mark.parametrize(
    "facts_factory",
    [
        lambda: (None, uuid4()),  # the notebook does not exist
        lambda: kitchen_facts(
            in_kitchen=False
        ),  # a kitchen notebook of a kitchen the caller is not in
    ],
)
def test_missing_or_not_visible_notebook_is_not_found_before_any_read(facts_factory) -> None:
    h = Harness(Draft(recipe=good_draft()))
    fact, notebook_id = facts_factory()
    if fact is not None:
        h.add(fact, notebook_id)

    with pytest.raises(NotebookNotFoundError):
        h.run(notebook_id)

    assert h.catalog.reads == []
    assert h.extractor.calls == []


def test_personal_notebook_with_no_membership_is_not_found() -> None:
    h = Harness(Draft(recipe=good_draft()))
    fact, notebook_id = personal_facts(uuid4(), role=None)  # type: ignore[arg-type]
    h.add(fact, notebook_id)

    with pytest.raises(NotebookNotFoundError):
        h.run(notebook_id)

    assert h.catalog.reads == []
    assert h.extractor.calls == []


def test_archived_kitchen_is_refused_before_any_assistant_call() -> None:
    h = Harness(Draft(recipe=good_draft()))
    fact, notebook_id = kitchen_facts(archived=True)
    h.add(fact, notebook_id)

    with pytest.raises(KitchenArchivedError):
        h.run(notebook_id)

    assert h.extractor.calls == []


def test_archived_kitchen_answers_not_found_to_a_non_member() -> None:
    h = Harness(Draft(recipe=good_draft()))
    fact, notebook_id = kitchen_facts(in_kitchen=False, archived=True)
    h.add(fact, notebook_id)

    with pytest.raises(NotebookNotFoundError):
        h.run(notebook_id)


def test_empty_text_is_refused_with_no_read_and_no_assistant_call() -> None:
    h = Harness(Draft(recipe=good_draft()))
    fact, notebook_id = personal_facts(uuid4())
    h.add(fact, notebook_id)

    with pytest.raises(TextEmptyError):
        h.run(notebook_id, text="   \n  ")

    assert h.notebooks.reads == []
    assert h.extractor.calls == []


def test_text_over_the_configured_limit_is_refused_after_trimming() -> None:
    h = Harness(Draft(recipe=good_draft()))
    fact, notebook_id = personal_facts(uuid4())
    h.add(fact, notebook_id)

    with pytest.raises(TextTooLongError) as refused:
        h.run(notebook_id, text="x" * (MAX_CHARS + 1))

    assert str(refused.value) == f"That text is too long. Paste up to {MAX_CHARS} characters."
    assert h.notebooks.reads == []
    assert h.extractor.calls == []


def test_text_at_the_limit_after_trimming_is_accepted() -> None:
    h = Harness(Draft(recipe=good_draft()))
    fact, notebook_id = personal_facts(uuid4())
    h.add(fact, notebook_id)

    outcome = h.run(notebook_id, text="  " + "x" * MAX_CHARS + "  ")

    assert isinstance(outcome, CapturedDraft)


@pytest.mark.parametrize(
    "result",
    [
        NotARecipe(reason=NotRecipeReason.QUESTION_OR_REQUEST, ingredient="butter"),
        NotARecipe(reason=NotRecipeReason.MULTIPLE_RECIPES),
        Unavailable(),
        LimitReached(retry_after_seconds=30),
        AIProviderError(),
    ],
)
def test_non_draft_results_pass_through_unchanged(result) -> None:
    h = Harness(result)
    fact, notebook_id = personal_facts(uuid4())
    h.add(fact, notebook_id)

    assert h.run(notebook_id) == result


class _Collect(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def test_log_keeps_length_and_outcome_and_never_the_text() -> None:
    secret = "PASTED-SECRET-TEXT in a recipe"
    h = Harness(Draft(recipe=good_draft()))
    fact, notebook_id = personal_facts(uuid4())
    h.add(fact, notebook_id)

    # Read the module's own logger, so other tests' logging setup cannot hide the record.
    logger = logging.getLogger("application.recipe_capture")
    collector = _Collect()
    previous = (logger.disabled, logger.level)
    logger.disabled, logger.level = False, logging.INFO
    logger.addHandler(collector)
    try:
        h.run(notebook_id, text=secret)
    finally:
        logger.removeHandler(collector)
        logger.disabled, logger.level = previous

    messages = " ".join(collector.messages)
    assert "outcome=Draft" in messages
    assert f"chars={len(secret)}" in messages
    assert "PASTED-SECRET" not in messages
