"""Translation job, AI step, with fake ports (spec 073, T024). No database."""

from __future__ import annotations

from application.translate_ingredients import TranslateIngredients
from domain.ingredient_discovery import Candidate, RecipeLineName
from domain.ingredient_translation import (
    IngredientTranslationResult,
    TranslationUnavailable,
    TranslationUnparseable,
)
from tests.catalog_translation_fakes import FakeIngredientTranslator
from tests.translate_job_fakes import Clock, EmitLog, FakeCatalog, FakeLock, FakeRunLog

VALID_ONION = IngredientTranslationResult(True, "cebolla")
VALID_GARLIC = IngredientTranslationResult(True, "ajo")


def job(
    catalog: FakeCatalog,
    translator: FakeIngredientTranslator,
    runs: FakeRunLog | None = None,
    batch_size: int = 50,
) -> TranslateIngredients:
    return TranslateIngredients(
        catalog=catalog,
        runs=runs or FakeRunLog(),
        lock=FakeLock(),
        translator=translator,
        model="model-x",
        batch_size=batch_size,
        clock=Clock(),
        emit=EmitLog(),
    )


def english_catalog(*names: str) -> FakeCatalog:
    return FakeCatalog(lines=[RecipeLineName(n, "en") for n in names], recipe_count=1)


def test_one_call_per_standard_ingredient() -> None:
    catalog = english_catalog("onion", "garlic")
    translator = FakeIngredientTranslator(results={"onion": VALID_ONION, "garlic": VALID_GARLIC})
    job(catalog, translator).run()
    assert sorted(call.name for call in translator.calls) == ["garlic", "onion"]


def test_a_valid_answer_saves_the_other_language_as_ai() -> None:
    catalog = english_catalog("onion")
    translator = FakeIngredientTranslator(results={"onion": VALID_ONION})
    summary = job(catalog, translator).run()
    assert summary.translated == 1
    names = catalog.names_for("onion")
    assert names["es"] == ("cebolla", "ai")
    assert catalog.ingredients["onion"].model == "model-x"
    assert catalog.ingredients["onion"].ai_checked_at is not None


def test_an_invalid_answer_saves_nothing_but_is_checked() -> None:
    catalog = english_catalog("onion")
    translator = FakeIngredientTranslator(
        results={"onion": IngredientTranslationResult(False, None)}
    )
    summary = job(catalog, translator).run()
    assert summary.rejected == 1
    assert "es" not in catalog.names_for("onion")
    assert catalog.ingredients["onion"].ai_checked_at is not None


def test_a_second_run_calls_the_model_zero_times() -> None:
    catalog = english_catalog("onion")
    translator = FakeIngredientTranslator(results={"onion": VALID_ONION})
    runs = FakeRunLog()
    job(catalog, translator, runs).run()
    job(catalog, translator, runs).run()
    assert len(translator.calls) == 1


def test_a_failed_call_leaves_the_ingredient_unchecked_for_the_next_run() -> None:
    catalog = english_catalog("onion")
    translator = FakeIngredientTranslator(failures={"onion": TranslationUnavailable})
    summary = job(catalog, translator).run()
    assert summary.failed == 1
    assert catalog.ingredients["onion"].ai_checked_at is None


def test_an_unparseable_answer_is_a_failure_not_a_result() -> None:
    catalog = english_catalog("onion")
    translator = FakeIngredientTranslator(failures={"onion": TranslationUnparseable})
    summary = job(catalog, translator).run()
    assert summary.failed == 1
    assert catalog.ingredients["onion"].ai_checked_at is None


def test_one_failing_item_does_not_stop_the_others() -> None:
    catalog = english_catalog("onion", "garlic")
    translator = FakeIngredientTranslator(
        results={"garlic": VALID_GARLIC},
        failures={"onion": TranslationUnavailable},
    )
    summary = job(catalog, translator).run()
    assert (summary.failed, summary.translated) == (1, 1)
    assert catalog.ingredients["garlic"].ai_checked_at is not None


def test_a_quota_error_stops_the_run_early() -> None:
    from domain.ingredient_translation import TranslationQuotaExceeded

    catalog = english_catalog("onion", "garlic")
    translator = FakeIngredientTranslator(failures={"onion": TranslationQuotaExceeded})
    summary = job(catalog, translator).run()
    assert len(translator.calls) == 1
    assert summary.failed == 1
    assert catalog.ingredients["garlic"].ai_checked_at is None


def test_batch_size_caps_the_calls_per_run() -> None:
    catalog = english_catalog("onion", "garlic", "basil")
    translator = FakeIngredientTranslator()
    job(catalog, translator, batch_size=2).run()
    assert len(translator.calls) == 2


def test_a_name_already_in_the_other_language_makes_no_call() -> None:
    catalog = english_catalog("onion")
    catalog.add_discovered([Candidate(key="onion", name="onion", language="en")])
    catalog.ingredients["onion"].names["es"] = ("cebolla", "admin")
    translator = FakeIngredientTranslator()
    summary = job(catalog, translator).run()
    assert translator.calls == []
    assert summary.translated == 0
    assert catalog.ingredients["onion"].ai_checked_at is not None
