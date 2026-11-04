"""Meaning search against fake ports (spec 019 US2, contracts/search-service.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from application.ports import RecipeDetail, RecipeLineDetail
from application.recipe_extraction import (
    AIProviderError,
    InvalidOutput,
    LimitReached,
    Unavailable,
)
from application.recipe_search import (
    MarkSearchResultUsed,
    SearchQuestionNotEmbedded,
    SearchRecipesCommand,
    SearchRecipesService,
)
from domain.errors import (
    InvalidSearchQuestionError,
    KitchenNotFoundError,
    NotebookNotFoundError,
)
from domain.recipe_search import Kitchen, MyNotebooks, OneNotebook, SearchFilters
from tests.embedding_fakes import (
    FakeEmbedder,
    FakeRecipeEmbeddings,
    FakeSearchRecords,
    fake_vector,
)
from tests.test_notebooks_application import (
    World,
    _join,
    _kitchen,
    _kitchen_notebook,
    _personal,
    _world,
)

ANA, BEN, CARLA = uuid4(), uuid4(), uuid4()
NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)


class Harness:
    def __init__(self, embedder: FakeEmbedder | None = None, minimum: float = 0.65) -> None:
        self.world: World = _world({ANA: "ana", BEN: "ben", CARLA: "carla"})
        self.embeddings = FakeRecipeEmbeddings()
        self.embedder = embedder or FakeEmbedder()
        self.records = FakeSearchRecords()
        self.service = SearchRecipesService(
            self.world.kitchens,
            self.world.notebooks,
            self.embeddings,
            self.embedder,
            self.records,
            strategy="toon",
            min_closeness=minimum,
            timeout_s=10.0,
        )

    def recipe(self, notebook_id: UUID, title: str, *names: str) -> UUID:
        detail = RecipeDetail(
            id=uuid4(),
            notebook_id=notebook_id,
            title=title,
            base_servings=2,
            servings_estimated=False,
            author_alias=None,
            lines=tuple(
                RecipeLineDetail(name, False, 1.0, "unit", None, None, None)
                for name in (names or ("rice",))
            ),
            steps=("Cook.",),
            source_type="text",
            source_url=None,
            created_at=NOW,
            updated_at=NOW,
        )
        self.embeddings.add(detail)
        self.embeddings.write_if_current(
            detail.id, NOW, self.embedder.model, fake_vector(title), "toon", 5
        )
        return detail.id

    def search(self, actor: UUID, scope, question: str = "rice", **filters):  # noqa: ANN001, ANN003, ANN201
        return self.service.execute(
            SearchRecipesCommand(
                actor_user_id=actor,
                scope=scope,
                question=question,
                feature="test",
                filters=SearchFilters(**filters),
            )
        )


def _ids(answer) -> set[UUID]:  # noqa: ANN001
    return {hit.recipe_id for hit in answer.results}


def test_kitchen_scope_reads_only_that_kitchen() -> None:
    h = Harness()
    home = _kitchen(h.world, ANA)
    other = _kitchen(h.world, BEN)
    mine = h.recipe(_kitchen_notebook(h.world, home, "Home", ANA), "tomato rice")
    h.recipe(_kitchen_notebook(h.world, other, "Other", BEN), "rice soup")
    h.recipe(_personal(h.world, ANA, "ana's Notebook"), "rice salad")

    assert _ids(h.search(ANA, Kitchen(home))) == {mine}
    assert "kitchen_ids_for" in h.world.notebooks.calls


def test_my_notebooks_reads_only_personal_notebooks() -> None:
    h = Harness()
    home = _kitchen(h.world, ANA)
    first = h.recipe(_personal(h.world, ANA, "ana's Notebook"), "tomato rice")
    second = h.recipe(_personal(h.world, ANA, "ana's second"), "rice soup")
    shared_nb = _personal(h.world, BEN, "ben's Notebook")
    h.world.notebooks.roles[(shared_nb, ANA)] = "member"
    shared = h.recipe(shared_nb, "rice cake")
    h.recipe(_kitchen_notebook(h.world, home, "Home", ANA), "kitchen rice")
    h.recipe(_personal(h.world, CARLA, "carla's Notebook"), "carla rice")

    assert _ids(h.search(ANA, MyNotebooks())) == {first, second, shared}


def test_one_notebook_reads_only_it() -> None:
    h = Harness()
    nb = _personal(h.world, ANA, "ana's Notebook")
    only = h.recipe(nb, "tomato rice")
    h.recipe(_personal(h.world, ANA, "ana's second"), "rice")

    assert _ids(h.search(ANA, OneNotebook(nb), "rice")) == {only}


def test_a_non_member_kitchen_is_not_found_and_nothing_is_called() -> None:
    h = Harness()
    other = _kitchen(h.world, BEN)
    h.recipe(_kitchen_notebook(h.world, other, "Other", BEN), "rice")

    with pytest.raises(KitchenNotFoundError):
        h.search(ANA, Kitchen(other))
    with pytest.raises(KitchenNotFoundError):
        h.search(ANA, Kitchen(uuid4()))
    assert h.embedder.calls == 0 and h.records.events == {}


def test_a_notebook_without_access_is_not_found_and_nothing_is_called() -> None:
    h = Harness()
    bens = _personal(h.world, BEN, "ben's Notebook")
    other = _kitchen(h.world, BEN)
    kitchen_nb = _kitchen_notebook(h.world, other, "Other", BEN)

    for notebook_id in (bens, kitchen_nb, uuid4()):
        with pytest.raises(NotebookNotFoundError):
            h.search(ANA, OneNotebook(notebook_id))
    assert h.embedder.calls == 0 and h.records.events == {}


def test_a_kitchen_member_reads_a_kitchen_notebook() -> None:
    h = Harness()
    home = _kitchen(h.world, BEN)
    _join(h.world, home, ANA)
    nb = _kitchen_notebook(h.world, home, "Home", BEN)
    recipe = h.recipe(nb, "rice")

    assert _ids(h.search(ANA, OneNotebook(nb))) == {recipe}


def test_an_empty_scope_returns_nothing_without_a_call_or_a_record() -> None:
    h = Harness()

    answer = h.search(ANA, MyNotebooks())

    assert answer.search_id is None and answer.results == ()
    assert h.embedder.calls == 0 and h.records.events == {}


def test_an_empty_question_is_refused_first() -> None:
    h = Harness()
    with pytest.raises(InvalidSearchQuestionError):
        h.search(ANA, Kitchen(uuid4()), "   ")
    assert h.embedder.calls == 0


@pytest.mark.parametrize(
    "failure",
    [LimitReached(retry_after_seconds=30), Unavailable(), InvalidOutput(), AIProviderError()],
)
def test_an_embedder_failure_is_raised_unchanged_and_nothing_is_recorded(failure) -> None:  # noqa: ANN001
    h = Harness(FakeEmbedder(failure=failure))
    h.recipe(_personal(h.world, ANA, "ana's Notebook"), "rice")

    with pytest.raises(SearchQuestionNotEmbedded) as caught:
        h.search(ANA, MyNotebooks())

    assert caught.value.outcome is failure
    assert h.records.events == {}


def test_hits_are_marked_against_the_minimum_closest_first() -> None:
    embedder = FakeEmbedder()
    h = Harness(embedder, minimum=0.99)
    nb = _personal(h.world, ANA, "ana's Notebook")
    exact = h.recipe(nb, "tomato rice")
    other = h.recipe(nb, "lentil soup")
    embedder.query_vector = fake_vector("tomato rice")

    answer = h.search(ANA, MyNotebooks(), "tomato rice")

    assert [hit.recipe_id for hit in answer.results] == [exact, other]
    assert answer.results[0].mark == "close"
    assert answer.results[1].mark == "weak"
    assert answer.results[0].score == pytest.approx(1.0)


def test_at_most_five_results() -> None:
    h = Harness()
    nb = _personal(h.world, ANA, "ana's Notebook")
    for number in range(8):
        h.recipe(nb, f"rice {number}")

    assert len(h.search(ANA, MyNotebooks()).results) == 5


def test_one_event_is_recorded_per_search_even_with_no_hit() -> None:
    h = Harness()
    nb = _personal(h.world, ANA, "ana's Notebook")
    h.recipe(nb, "tomato rice", "rice", "tomato")

    empty = h.search(ANA, MyNotebooks(), ingredient_names=("chicken",))
    full = h.search(ANA, MyNotebooks())

    assert empty.results == () and empty.search_id is not None
    event, hits = h.records.events[empty.search_id]
    assert hits == () and event.feature == "test" and event.scope_kind == "my_notebooks"
    assert event.model == "fake-embed" and event.strategy == "toon"
    event, hits = h.records.events[full.search_id]
    assert [hit.rank for hit in hits] == [1] and hits[0].mark in {"close", "weak"}


def test_mark_used_sets_once_and_ignores_unknown_pairs() -> None:
    h = Harness()
    recipe = h.recipe(_personal(h.world, ANA, "ana's Notebook"), "rice")
    answer = h.search(ANA, MyNotebooks())
    used = MarkSearchResultUsed(h.records)

    assert used.execute(answer.search_id, recipe) is True
    first = h.records.used[(answer.search_id, recipe)]
    assert used.execute(answer.search_id, recipe) is True
    assert h.records.used[(answer.search_id, recipe)] == first
    assert used.execute(answer.search_id, uuid4()) is False
    assert used.execute(uuid4(), recipe) is False
