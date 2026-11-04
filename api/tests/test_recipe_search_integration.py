"""Meaning search against Postgres with invented people (spec 019 US2, SC-004, SC-007, SC-008).

Embeddings are written straight through write_if_current from FakeEmbedder vectors, so no
service is called. Requires DATABASE_URL.
"""

from __future__ import annotations

import itertools
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from adapters.persistence.embeddings import SqlAlchemyRecipeEmbeddings
from adapters.persistence.models import KitchenMembershipModel
from adapters.persistence.notebooks import SqlAlchemyNotebookRepository
from adapters.persistence.repositories import SqlAlchemyKitchenRepository
from adapters.persistence.search_records import SqlAlchemySearchRecords
from adapters.persistence.vector import to_vector_text
from application.recipe_search import (
    MarkSearchResultUsed,
    SearchRecipesCommand,
    SearchRecipesService,
)
from domain.errors import KitchenNotFoundError, NotebookNotFoundError
from domain.recipe_search import Kitchen, MyNotebooks, OneNotebook, SearchFilters
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests import embedding_db as build
from tests.embedding_fakes import FakeEmbedder, fake_vector
from tests.integration_db import database_url

pytestmark = pytest.mark.skipif(
    database_url() is None,
    reason="DATABASE_URL not set — Postgres 16 required for integration tests",
)


def _service(db: Session, embedder: FakeEmbedder | None = None) -> SearchRecipesService:
    return SearchRecipesService(
        SqlAlchemyKitchenRepository(db),
        SqlAlchemyNotebookRepository(db),
        SqlAlchemyRecipeEmbeddings(db),
        embedder or FakeEmbedder(dimension=build.DIM, model=build.MODEL),
        SqlAlchemySearchRecords(db),
        strategy="toon",
        min_closeness=0.65,
        timeout_s=10.0,
    )


def _search(db: Session, actor: UUID, scope, question: str = "rice", **filters):  # noqa: ANN001, ANN003, ANN201
    return _service(db).execute(
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


class Town:
    """Two kitchens and three people, with personal notebooks shared one way (SC-004)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.ana = build.user(db, "ana")
        self.ben = build.user(db, "ben")
        self.carla = build.user(db, "carla")
        self.kitchen_a = build.kitchen(db, self.ana)
        build.join_kitchen(db, self.kitchen_a, self.ben)
        self.kitchen_b = build.kitchen(db, self.carla)
        self.kitchen_c = build.kitchen(db, self.ben)
        self.kn_a = build.kitchen_notebook(db, self.kitchen_a, self.ana)
        self.kn_b = build.kitchen_notebook(db, self.kitchen_b, self.carla)
        self.kn_c = build.kitchen_notebook(db, self.kitchen_c, self.ben)
        self.ana_1 = build.personal_notebook(db, self.ana, "ana one")
        self.ana_2 = build.personal_notebook(db, self.ana, "ana two")
        self.ben_1 = build.personal_notebook(db, self.ben, "ben one")
        build.add_member(db, self.ben_1, self.ana)
        self.carla_1 = build.personal_notebook(db, self.carla, "carla one")
        self.recipes: dict[UUID, list[UUID]] = {}
        for notebook in (
            self.kn_a,
            self.kn_b,
            self.kn_c,
            self.ana_1,
            self.ana_2,
            self.ben_1,
            self.carla_1,
        ):
            self.recipes[notebook] = [
                self.add(notebook, f"rice dish {n} of {notebook.hex[:6]}", ("rice", "chicken"))
                for n in range(2)
            ]

    def add(self, notebook: UUID, title: str, ingredients=("rice",), **kwargs) -> UUID:  # noqa: ANN001, ANN003
        recipe = build.recipe(self.db, notebook, title, ingredients, **kwargs)
        assert build.embed(self.db, recipe)
        return recipe

    def readable(self, person: UUID) -> dict[str, set[UUID]]:
        """Notebook ids each scope may return for the person."""
        kitchens = {
            self.ana: {self.kitchen_a: {self.kn_a}},
            self.ben: {self.kitchen_a: {self.kn_a}, self.kitchen_c: {self.kn_c}},
            self.carla: {self.kitchen_b: {self.kn_b}},
        }[person]
        personal = {
            self.ana: {self.ana_1, self.ana_2, self.ben_1},
            self.ben: {self.ben_1},
            self.carla: {self.carla_1},
        }[person]
        return {"kitchens": kitchens, "personal": personal}

    def notebook_of(self, recipe: UUID) -> UUID:
        return next(nb for nb, ids in self.recipes.items() if recipe in ids)


@pytest.fixture
def town(db_session: Session) -> Town:
    return Town(db_session)


def test_kitchen_scope_returns_only_that_kitchen(town: Town) -> None:
    answer = _search(town.db, town.ana, Kitchen(town.kitchen_a))
    assert _ids(answer) == set(town.recipes[town.kn_a])


def test_my_notebooks_returns_only_personal_notebooks(town: Town) -> None:
    answer = _search(town.db, town.ana, MyNotebooks())
    allowed = {r for nb in (town.ana_1, town.ana_2, town.ben_1) for r in town.recipes[nb]}
    assert _ids(answer) <= allowed and len(answer.results) == 5


def test_one_notebook_returns_only_it_even_with_closer_recipes_elsewhere(town: Town) -> None:
    closest = town.add(town.ana_2, "creamy mushroom soup")
    answer = _search(town.db, town.ana, OneNotebook(town.ana_1), "creamy mushroom soup")
    assert _ids(answer) == set(town.recipes[town.ana_1])
    assert closest not in _ids(answer)


def test_non_members_get_not_found(town: Town) -> None:
    with pytest.raises(KitchenNotFoundError):
        _search(town.db, town.ana, Kitchen(town.kitchen_b))
    with pytest.raises(NotebookNotFoundError):
        _search(town.db, town.ana, OneNotebook(town.carla_1))
    with pytest.raises(NotebookNotFoundError):
        _search(town.db, town.carla, OneNotebook(town.kn_a))


def test_the_ingredient_filter_needs_every_name(town: Town) -> None:
    only_chicken = town.add(town.ana_1, "plain chicken", ("chicken",))
    both = town.add(town.ana_1, "Chicken and rice", ("Chicken", "arroz", "rice"))
    accented = town.add(town.ana_1, "limón chicken rice", ("limón", "chicken", "rice"))

    answer = _search(
        town.db, town.ana, OneNotebook(town.ana_1), ingredient_names=("chicken", "RICE")
    )
    assert only_chicken not in _ids(answer)
    assert both in _ids(answer)

    lemon = _search(town.db, town.ana, OneNotebook(town.ana_1), ingredient_names=("limon",))
    assert _ids(lemon) == {accented}


def test_author_dates_and_exclude_filters(town: Town) -> None:
    early = datetime(2026, 1, 10, tzinfo=UTC)
    late = datetime(2026, 6, 10, tzinfo=UTC)
    by_ben = town.add(town.ben_1, "ben's early rice", author_id=town.ben, created_at=early)
    by_ana = town.add(town.ben_1, "ana's late rice", author_id=town.ana, created_at=late)

    scope = OneNotebook(town.ben_1)
    assert _ids(_search(town.db, town.ana, scope, author_id=town.ben)) == {by_ben}
    assert by_ana in _ids(_search(town.db, town.ana, scope, created_after=late - timedelta(days=1)))
    assert by_ben not in _ids(
        _search(town.db, town.ana, scope, created_after=late - timedelta(days=1))
    )
    assert _ids(_search(town.db, town.ana, scope, created_before=early + timedelta(days=1))) == {
        by_ben
    }
    assert by_ben not in _ids(_search(town.db, town.ana, scope, exclude_recipe_ids=(by_ben,)))


def test_fewer_matches_than_five_return_only_those(town: Town) -> None:
    answer = _search(town.db, town.ana, OneNotebook(town.ana_2))
    assert _ids(answer) == set(town.recipes[town.ana_2])


def test_stale_embeddings_and_other_models_are_never_returned(town: Town) -> None:
    stale, other_model = town.recipes[town.ana_1]
    build.bump(town.db, stale)
    town.db.execute(
        text("UPDATE recipe_embedding SET model = 'older-model' WHERE recipe_id = :id"),
        {"id": other_model},
    )

    assert _search(town.db, town.ana, OneNotebook(town.ana_1)).results == ()


def test_an_edited_recipe_is_not_found_by_its_old_content(town: Town) -> None:
    recipe = town.add(town.ana_2, "old secret title")
    embedder = FakeEmbedder(dimension=build.DIM, model=build.MODEL)
    embedder.query_vector = fake_vector("old secret title", build.DIM)
    service = _service(town.db, embedder)
    command = SearchRecipesCommand(
        actor_user_id=town.ana, scope=OneNotebook(town.ana_2), question="old", feature="test"
    )
    assert recipe in _ids(service.execute(command))
    for _ in range(3):
        build.bump(town.db, recipe)
        assert recipe not in _ids(service.execute(command))


def test_results_are_closest_first_and_at_most_five(town: Town) -> None:
    target = town.add(town.ana_1, "exact question text")
    embedder = FakeEmbedder(dimension=build.DIM, model=build.MODEL)
    embedder.query_vector = fake_vector("exact question text", build.DIM)
    for n in range(6):
        town.add(town.ana_1, f"filler {n}")

    answer = _service(town.db, embedder).execute(
        SearchRecipesCommand(town.ana, OneNotebook(town.ana_1), "exact question text", "test")
    )

    assert len(answer.results) == 5
    assert answer.results[0].recipe_id == target
    assert answer.results[0].score == pytest.approx(1.0) and answer.results[0].mark == "close"
    scores = [hit.score for hit in answer.results]
    assert scores == sorted(scores, reverse=True)


def test_no_result_ever_comes_from_a_notebook_the_person_may_not_read(town: Town) -> None:
    filter_sets = [
        {},
        {"ingredient_names": ("chicken",)},
        {"ingredient_names": ("rice", "chicken")},
        {"created_after": datetime(2000, 1, 1, tzinfo=UTC)},
        {"author_id": town.carla},
        {"exclude_recipe_ids": tuple(town.recipes[town.kn_a])},
    ]
    for person, filters in itertools.product((town.ana, town.ben, town.carla), filter_sets):
        allowed = town.readable(person)
        scopes = [(Kitchen(k), nbs) for k, nbs in allowed["kitchens"].items()]
        scopes.append((MyNotebooks(), allowed["personal"]))
        scopes.extend((OneNotebook(nb), {nb}) for nb in allowed["personal"])
        for scope, notebooks in scopes:
            for hit in _search(town.db, person, scope, **filters).results:
                assert hit.notebook_id in notebooks, (person, scope, filters)
                assert town.notebook_of(hit.recipe_id) in notebooks


def test_an_archived_kitchen_stays_searchable_for_its_members(town: Town) -> None:
    town.db.execute(
        text("UPDATE kitchens SET is_archived = true WHERE id = :id"), {"id": town.kitchen_a}
    )
    assert _ids(_search(town.db, town.ben, Kitchen(town.kitchen_a))) == set(town.recipes[town.kn_a])


def test_a_removed_member_is_not_found_on_the_next_search(town: Town) -> None:
    assert _search(town.db, town.ben, Kitchen(town.kitchen_a)).results
    town.db.query(KitchenMembershipModel).filter_by(
        kitchen_id=town.kitchen_a, user_id=town.ben
    ).delete()
    town.db.flush()
    with pytest.raises(KitchenNotFoundError):
        _search(town.db, town.ben, Kitchen(town.kitchen_a))


def test_every_search_is_recorded_and_records_go_with_their_recipe(town: Town) -> None:
    empty = _search(town.db, town.ana, OneNotebook(town.ana_1), ingredient_names=("saffron",))
    full = _search(town.db, town.ana, OneNotebook(town.ana_1))

    events = town.db.execute(
        text("SELECT * FROM search_event WHERE id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": [empty.search_id, full.search_id]},
    ).all()
    by_id = {row.id: row for row in events}
    assert by_id[empty.search_id].result_count == 0
    assert by_id[full.search_id].result_count == 2
    assert by_id[full.search_id].scope_kind == "notebook"
    assert by_id[full.search_id].feature == "test"
    rows = town.db.execute(
        text("SELECT * FROM search_result WHERE search_id = :id ORDER BY rank"),
        {"id": full.search_id},
    ).all()
    assert [row.rank for row in rows] == [1, 2]
    assert [row.recipe_id for row in rows] == [hit.recipe_id for hit in full.results]
    assert all(row.mark in {"close", "weak"} for row in rows)

    used = MarkSearchResultUsed(SqlAlchemySearchRecords(town.db))
    assert used.execute(full.search_id, rows[0].recipe_id)
    assert not used.execute(full.search_id, uuid4())

    town.db.execute(text("DELETE FROM recipe WHERE id = :id"), {"id": rows[0].recipe_id})
    remaining = town.db.scalar(
        text("SELECT count(*) FROM search_result WHERE search_id = :id"), {"id": full.search_id}
    )
    assert remaining == 1


def test_records_report_bands_and_clean_up(town: Town) -> None:
    records = SqlAlchemySearchRecords(town.db)
    answer = _search(town.db, town.ana, OneNotebook(town.ana_1))
    MarkSearchResultUsed(records).execute(answer.search_id, answer.results[0].recipe_id)
    town.db.execute(
        text("UPDATE search_event SET created_at = now() - interval '181 days' WHERE id = :id"),
        {"id": answer.search_id},
    )

    bands = records.score_bands(0.05)
    assert sum(band.shown for band in bands) >= 2
    assert sum(band.used for band in bands) >= 1
    assert all(round(band.high - band.low, 6) == 0.05 for band in bands)

    deleted = records.delete_older_than(datetime.now(UTC) - timedelta(days=180))
    assert deleted >= 1
    assert (
        town.db.scalar(
            text("SELECT count(*) FROM search_event WHERE id = :id"), {"id": answer.search_id}
        )
        == 0
    )


def test_a_search_over_1000_recipes_takes_under_a_second(db_session: Session) -> None:
    owner = build.user(db_session, "dora")
    kitchen_id = build.kitchen(db_session, owner)
    notebook = build.kitchen_notebook(db_session, kitchen_id, owner)
    rows = [
        {"id": uuid4(), "title": f"recipe {n}", "vector": to_vector_text(fake_vector(str(n), 768))}
        for n in range(1000)
    ]
    db_session.execute(
        text(
            "INSERT INTO recipe (id, notebook_id, title, base_servings) "
            "VALUES (:id, :notebook, :title, 2)"
        ),
        [{**row, "notebook": notebook} for row in rows],
    )
    db_session.execute(
        text(
            "INSERT INTO recipe_embedding (recipe_id, model, embedding, strategy_used,"
            " recipe_updated_at) SELECT CAST(:id AS uuid), :model, CAST(:vector AS vector),"
            " 'toon', r.updated_at FROM recipe r WHERE r.id = CAST(:id AS uuid)"
        ),
        [{**row, "model": build.MODEL} for row in rows],
    )
    service = _service(db_session)
    command = SearchRecipesCommand(owner, Kitchen(kitchen_id), "something to cook", "test")
    service.execute(command)  # warm the plan

    started = time.perf_counter()
    answer = service.execute(command)
    elapsed = time.perf_counter() - started

    assert len(answer.results) == 5
    assert elapsed < 1.0, elapsed
