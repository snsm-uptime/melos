"""Translation job, discovery part, with fake ports (spec 073, T017). No database."""

from __future__ import annotations

from application.translate_ingredients import TranslateIngredients
from domain.ingredient_discovery import RecipeLineName
from domain.ingredient_translation import IngredientTranslationResult
from tests.catalog_translation_fakes import FakeIngredientTranslator
from tests.translate_job_fakes import Clock, EmitLog, FakeCatalog, FakeLock, FakeRunLog


def job(
    catalog: FakeCatalog, translator: FakeIngredientTranslator, runs: FakeRunLog, emit: EmitLog
) -> TranslateIngredients:
    return TranslateIngredients(
        catalog=catalog,
        runs=runs,
        lock=FakeLock(),
        translator=translator,
        model="model-x",
        batch_size=50,
        clock=Clock(),
        emit=emit,
    )


def test_discovery_creates_a_standard_ingredient_once() -> None:
    catalog = FakeCatalog(lines=[RecipeLineName("onion", "en")], recipe_count=1)
    summary = job(catalog, FakeIngredientTranslator(), FakeRunLog(), EmitLog()).run()
    assert summary.status == "succeeded"
    assert summary.found == 1
    assert list(catalog.ingredients) == ["onion"]


def test_a_repeated_run_creates_no_duplicate() -> None:
    catalog = FakeCatalog(lines=[RecipeLineName("onion", "en")], recipe_count=1)
    runs = FakeRunLog()
    translator = FakeIngredientTranslator()
    first = job(catalog, translator, runs, EmitLog()).run()
    second = job(catalog, translator, runs, EmitLog()).run()
    assert first.found == 1
    assert second.found == 0
    assert len(catalog.ingredients) == 1


def test_a_run_with_no_new_names_makes_no_translator_call() -> None:
    catalog = FakeCatalog(lines=[RecipeLineName("onion", "en")], recipe_count=1)
    translator = FakeIngredientTranslator(
        results={"onion": IngredientTranslationResult(True, "cebolla")}
    )
    runs = FakeRunLog()
    job(catalog, translator, runs, EmitLog()).run()
    calls_after_first = len(translator.calls)
    job(catalog, translator, runs, EmitLog()).run()
    assert calls_after_first == 1
    assert len(translator.calls) == calls_after_first


def test_discovery_emits_counts_without_names() -> None:
    catalog = FakeCatalog(lines=[RecipeLineName("onion", "en")], recipe_count=2)
    emit = EmitLog()
    job(catalog, FakeIngredientTranslator(), FakeRunLog(), emit).run()
    discovery = next(fields for event, fields in emit.events if event == "discovery.done")
    assert discovery["recipes_scanned"] == 2
    assert discovery["found"] == 1
    assert all("onion" not in str(fields) for _, fields in emit.events)


def test_busy_lock_records_a_skipped_run() -> None:
    runs = FakeRunLog()
    emit = EmitLog()
    use_case = TranslateIngredients(
        catalog=FakeCatalog(),
        runs=runs,
        lock=FakeLock(busy=True),
        translator=FakeIngredientTranslator(),
        model="model-x",
        batch_size=50,
        clock=Clock(),
        emit=emit,
    )
    assert use_case.run().status == "skipped"
    assert runs.runs[0]["status"] == "skipped"
    assert emit.names() == ["run.skipped"]
