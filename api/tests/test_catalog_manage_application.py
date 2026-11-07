"""Catalog management use cases against fake ports (spec 043)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from application.catalog_manage import (
    DeleteNameService,
    DismissPairService,
    GetCatalogService,
    MergeCommand,
    MergePreviewCommand,
    MergePreviewService,
    MergeService,
    RenameCommand,
    RenameService,
    SplitService,
    SuggestPairsService,
)
from domain.errors import (
    AIUnavailableError,
    CatalogNameBlankError,
    CatalogNameChangedError,
    CatalogNameExistsError,
    CatalogNameInUseError,
    CatalogReadOnlyError,
    NotebookNotFoundError,
    SameIngredientError,
)
from domain.ingredient_catalog import CatalogEntry
from tests.catalog_manage_fakes import FakeManagedCatalog, FakePairSuggester, FakePlaces
from tests.embedding_fakes import FakeEmbeddingJobs
from tests.test_notebooks_application import (
    World,
    _join,
    _kitchen,
    _kitchen_notebook,
    _personal,
    _world,
)

ANA, BEN, CAM = uuid4(), uuid4(), uuid4()


@pytest.fixture
def world() -> World:
    return _world({ANA: "ana", BEN: "ben", CAM: "cam"})


@pytest.fixture
def catalog() -> FakeManagedCatalog:
    return FakeManagedCatalog()


def _merge(
    world: World,
    catalog: FakeManagedCatalog,
    notebook_ids: list[UUID],
    *,
    places: FakePlaces | None = None,
    jobs: FakeEmbeddingJobs | None = None,
    actor: UUID = ANA,
):
    service = MergeService(world.notebooks, catalog, places or FakePlaces(), embedding_jobs=jobs)
    return service.execute(
        MergeCommand(
            actor_user_id=actor,
            merged="cebolla",
            kept="onion",
            merged_language="es",
            kept_language="en",
            notebook_ids=tuple(notebook_ids),
        )
    )


def _preview(world: World, catalog: FakeManagedCatalog, notebook_id: UUID, actor: UUID = ANA):
    return MergePreviewService(world.notebooks, catalog).execute(
        MergePreviewCommand(actor, notebook_id, "cebolla", "onion")
    )


# --- read ---------------------------------------------------------------------------------------


def test_the_catalog_lists_other_names_and_counts(
    world: World, catalog: FakeManagedCatalog
) -> None:
    notebook = _personal(world, ANA, "ana's Notebook")
    catalog.add(notebook, CatalogEntry("onion", "en", {"es": "cebolla"}), "salt")
    catalog.recipe(notebook, "es", "onion", "salt")
    view = GetCatalogService(world.notebooks, catalog).execute(ANA, notebook)
    assert view.can_write
    onion = view.item("onion")
    assert onion is not None and onion.recipe_count == 1 and onion.variants == {"es": "cebolla"}
    with pytest.raises(NotebookNotFoundError):
        GetCatalogService(world.notebooks, catalog).execute(BEN, notebook)


# --- merge preview (T021) -----------------------------------------------------------------------


def test_the_preview_lists_only_writable_notebooks_with_both_names(
    world: World, catalog: FakeManagedCatalog
) -> None:
    personal = _personal(world, ANA, "ana's Notebook")
    kitchen = _kitchen(world, ANA)
    shared = _kitchen_notebook(world, kitchen, "Home notebook", ANA)
    archived = _kitchen_notebook(world, _kitchen(world, ANA, archived=True), "Old", ANA)
    only_one = _personal(world, ANA, "Second")
    for notebook in (personal, shared, archived):
        catalog.add(notebook, "onion", "cebolla")
    catalog.add(only_one, "onion")
    catalog.recipe(personal, "es", "cebolla")
    catalog.recipe(shared, "es", "cebolla")
    catalog.recipe(shared, "en", "onion")
    catalog.recipe(shared, "en", "onion")

    preview = _preview(world, catalog, personal)

    assert {(n.notebook_id, n.recipe_count) for n in preview.notebooks} == {
        (personal, 1),
        (shared, 1),
    }
    assert (preview.merged_language, preview.kept_language) == ("es", "en")


def test_the_preview_falls_back_to_the_stored_language(
    world: World, catalog: FakeManagedCatalog
) -> None:
    personal = _personal(world, ANA, "ana's Notebook")
    catalog.add(personal, CatalogEntry("onion", "en"), "cebolla")
    preview = _preview(world, catalog, personal)
    assert (preview.merged_language, preview.kept_language) == (None, "en")


def test_the_preview_refuses_one_ingredient_and_read_only(
    world: World, catalog: FakeManagedCatalog
) -> None:
    personal = _personal(world, ANA, "ana's Notebook")
    catalog.add(personal, CatalogEntry("onion", "en", {"es": "cebolla"}))
    with pytest.raises(SameIngredientError):
        _preview(world, catalog, personal)
    archived = _kitchen_notebook(world, _kitchen(world, ANA, archived=True), "Old", ANA)
    catalog.add(archived, "onion", "cebolla")
    with pytest.raises(CatalogReadOnlyError):
        _preview(world, catalog, archived)


# --- merge (T021) -------------------------------------------------------------------------------


def test_a_merge_across_two_notebooks(world: World, catalog: FakeManagedCatalog) -> None:
    personal = _personal(world, ANA, "ana's Notebook")
    kitchen = _kitchen(world, ANA)
    shared = _kitchen_notebook(world, kitchen, "Home notebook", ANA)
    for notebook in (personal, shared):
        catalog.add(notebook, "onion", "cebolla")
    spanish = catalog.recipe(personal, "es", "cebolla")
    english = catalog.recipe(shared, "en", "onion")
    jobs = FakeEmbeddingJobs()

    result = _merge(world, catalog, [personal, shared], jobs=jobs)

    assert set(result.merged) == {(personal, 1), (shared, 0)}
    assert result.skipped == ()
    assert catalog.recipes[spanish].lines == ["onion"]
    assert catalog.recipes[english].lines == ["onion"]
    for notebook in (personal, shared):
        assert catalog.entries[notebook]["onion"].variants == {"es": "cebolla"}
        assert "cebolla" not in catalog.entries[notebook]
    assert jobs.enqueued == [spanish]


def test_a_notebook_whose_name_changed_is_skipped(
    world: World, catalog: FakeManagedCatalog
) -> None:
    first = _personal(world, ANA, "ana's Notebook")
    second = _personal(world, ANA, "Second")
    catalog.add(first, "onion", "cebolla")
    catalog.add(second, "onion", "cebolla")
    # Someone renamed "cebolla" in the second notebook after the preview listed it. (The real
    # race, under the row locks, is in the integration tests.)
    catalog.apply_rename(second, "cebolla", "cebollita")
    service = MergeService(world.notebooks, catalog, FakePlaces())
    result = service.execute(MergeCommand(ANA, "cebolla", "onion", "es", "en", (first, second)))
    assert result.merged == ((first, 0),)
    assert result.skipped == ((second, "name_changed"),)
    assert "cebollita" in catalog.entries[second]


def test_a_read_only_notebook_is_never_touched(world: World, catalog: FakeManagedCatalog) -> None:
    writable = _personal(world, ANA, "ana's Notebook")
    archived = _kitchen_notebook(world, _kitchen(world, ANA, archived=True), "Old", ANA)
    stranger = _personal(world, BEN, "ben's Notebook")
    for notebook in (writable, archived, stranger):
        catalog.add(notebook, "onion", "cebolla")

    result = _merge(world, catalog, [writable, archived, stranger])

    assert result.merged == ((writable, 0),)
    assert set(result.skipped) == {(archived, "no_access"), (stranger, "no_access")}
    assert "cebolla" in catalog.entries[archived]
    assert "cebolla" in catalog.entries[stranger]


def test_a_kitchen_member_may_merge_a_kitchen_notebook(
    world: World, catalog: FakeManagedCatalog
) -> None:
    kitchen = _kitchen(world, ANA)
    _join(world, kitchen, BEN)
    shared = _kitchen_notebook(world, kitchen, "Home notebook", ANA)
    catalog.add(shared, "onion", "cebolla")
    assert _merge(world, catalog, [shared], actor=BEN).merged == ((shared, 0),)


def test_places_move_to_the_kept_name(world: World, catalog: FakeManagedCatalog) -> None:
    notebook = _personal(world, ANA, "ana's Notebook")
    catalog.add(notebook, "onion", "cebolla")
    places = FakePlaces({(ANA, "cebolla"): "farmers_market", (BEN, "cebolla"): "bakery"})
    places.choices[(BEN, "onion")] = "butcher"

    _merge(world, catalog, [notebook], places=places)

    assert places.choices[(ANA, "onion")] == "farmers_market"
    # Ben's own choice for the kept name stays (FR-009).
    assert places.choices[(BEN, "onion")] == "butcher"


# --- rename (T036) ------------------------------------------------------------------------------


def _rename(world: World, catalog: FakeManagedCatalog, notebook: UUID, old: str, new: str, **kw):
    places = kw.pop("places", FakePlaces())
    service = RenameService(world.notebooks, catalog, places, embedding_jobs=kw.pop("jobs", None))
    return service.execute(RenameCommand(ANA, notebook, old, new, **kw))


def test_a_rename_rewrites_the_lines_and_moves_places(
    world: World, catalog: FakeManagedCatalog
) -> None:
    notebook = _personal(world, ANA, "ana's Notebook")
    catalog.add(notebook, "tomatoe")
    recipe = catalog.recipe(notebook, "en", "tomatoe")
    places = FakePlaces({(ANA, "tomatoe"): "farmers_market"})
    jobs = FakeEmbeddingJobs()

    result = _rename(world, catalog, notebook, "tomatoe", "Tomato", places=places, jobs=jobs)

    assert result.item.name == "tomato" and result.recipes_changed == 1
    assert catalog.recipes[recipe].lines == ["tomato"]
    assert places.choices == {(ANA, "tomato"): "farmers_market"}
    assert jobs.enqueued == [recipe]


def test_a_rename_to_an_existing_name_and_a_blank_name_are_refused(
    world: World, catalog: FakeManagedCatalog
) -> None:
    notebook = _personal(world, ANA, "ana's Notebook")
    catalog.add(notebook, "tomatoe", "tomato")
    with pytest.raises(CatalogNameExistsError) as raised:
        _rename(world, catalog, notebook, "tomatoe", "tomatoes")
    assert raised.value.existing == "tomato"
    with pytest.raises(CatalogNameBlankError):
        _rename(world, catalog, notebook, "tomatoe", "  ")


def test_a_rename_of_a_name_that_is_gone_reports_it(
    world: World, catalog: FakeManagedCatalog
) -> None:
    notebook = _personal(world, ANA, "ana's Notebook")
    catalog.add(notebook, "tomatoe")
    catalog.on_lock.append(lambda: catalog.apply_rename(notebook, "tomatoe", "tomato"))
    with pytest.raises(CatalogNameChangedError):
        _rename(world, catalog, notebook, "tomatoe", "tomatillo")


def test_setting_a_language_without_renaming(world: World, catalog: FakeManagedCatalog) -> None:
    notebook = _personal(world, ANA, "ana's Notebook")
    catalog.add(notebook, "garlic")
    result = _rename(world, catalog, notebook, "garlic", "garlic", language="en", set_language=True)
    assert result.item.language == "en" and result.recipes_changed == 0


# --- delete (T043) ------------------------------------------------------------------------------


def test_an_unused_name_is_deleted_and_a_used_one_refused(
    world: World, catalog: FakeManagedCatalog
) -> None:
    notebook = _personal(world, ANA, "ana's Notebook")
    catalog.add(notebook, "saffron", "onion")
    catalog.recipe(notebook, "en", "onion")
    catalog.recipe(notebook, "es", "onion")
    service = DeleteNameService(world.notebooks, catalog)

    service.execute(ANA, notebook, "saffron")
    assert "saffron" not in catalog.entries[notebook]
    with pytest.raises(CatalogNameInUseError) as raised:
        service.execute(ANA, notebook, "onion")
    assert raised.value.recipe_count == 2


# --- split (T053, application part) -------------------------------------------------------------


def test_a_split_variant_takes_back_its_language_s_lines(
    world: World, catalog: FakeManagedCatalog
) -> None:
    notebook = _personal(world, ANA, "ana's Notebook")
    catalog.add(notebook, CatalogEntry("onion", "en", {"es": "cebolla"}))
    spanish = catalog.recipe(notebook, "es", "onion")
    english = catalog.recipe(notebook, "en", "onion")
    jobs = FakeEmbeddingJobs()

    service = SplitService(world.notebooks, catalog, embedding_jobs=jobs)
    result = service.execute(ANA, notebook, "onion", "cebolla")

    assert result.split.name == "cebolla" and result.split.language == "es"
    assert result.kept.variants == {}
    assert catalog.recipes[spanish].lines == ["cebolla"]
    assert catalog.recipes[english].lines == ["onion"]
    assert jobs.enqueued == [spanish]


# --- pairs (T048) -------------------------------------------------------------------------------


def test_suggested_pairs_drop_invented_and_dismissed_ones(
    world: World, catalog: FakeManagedCatalog
) -> None:
    notebook = _personal(world, ANA, "ana's Notebook")
    catalog.add(notebook, CatalogEntry("garlic", "en"), "ajo", "flour", "harina")
    suggester = FakePairSuggester([("garlic", "ajo"), ("flour", "harina"), ("salt", "sal")])
    suggest = SuggestPairsService(world.notebooks, catalog, suggester)

    assert suggest.execute(ANA, notebook).pairs == (("garlic", "ajo"), ("flour", "harina"))
    # Only names and languages reach the model.
    assert ("garlic", "en") in suggester.calls[0]

    DismissPairService(world.notebooks, catalog).execute(ANA, notebook, "flour", "harina")
    assert suggest.execute(ANA, notebook).pairs == (("garlic", "ajo"),)


def test_suggestions_report_the_model_unavailable_and_refuse_read_only(
    world: World, catalog: FakeManagedCatalog
) -> None:
    notebook = _personal(world, ANA, "ana's Notebook")
    catalog.add(notebook, "garlic", "ajo")
    with pytest.raises(AIUnavailableError):
        SuggestPairsService(world.notebooks, catalog, FakePairSuggester(unavailable=True)).execute(
            ANA, notebook
        )
    archived = _kitchen_notebook(world, _kitchen(world, ANA, archived=True), "Old", ANA)
    catalog.add(archived, "garlic", "ajo")
    with pytest.raises(CatalogReadOnlyError):
        SuggestPairsService(world.notebooks, catalog, FakePairSuggester()).execute(ANA, archived)
