"""Use-case tests for recipe extraction, run against FakeRecipeExtractor (no network).

Covers the six results (FR-001, FR-002, FR-003 to FR-005), input refusal before
any call (FR-012), the timeout pass-through (FR-013), concurrency (FR-016) and
the stand-in (FR-010, SC-001, SC-007).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import replace

import pytest
from adapters.llm.fake_extractor import FakeRecipeExtractor
from adapters.llm.vocabulary import load_vocabulary
from application.recipe_extraction import (
    MAX_TEXT_CHARS,
    AIProviderError,
    Draft,
    DraftIncomplete,
    InvalidOutput,
    LimitReached,
    NotARecipe,
    NotRecipeReason,
    RecipeExtraction,
    RecipeTextRefusedError,
    Unavailable,
)
from domain.recipe_draft import DraftRecipe, IngredientLine, LineProblem, LineProblemKind

VOCABULARY = load_vocabulary()
ACCEPTANCE_TEXT = "Onion soup\n\n- a pinch of salt\n- 2 large onions\n\n1. Simmer with the salt."


def acceptance_draft() -> DraftRecipe:
    return DraftRecipe(
        title="Onion soup",
        base_servings=None,
        servings_estimated=False,
        main_ingredients=(),
        cuisines=(),
        ingredient_lines=(
            IngredientLine(name="salt", vague=True, note="a pinch of"),
            IngredientLine(name="onion", vague=False, quantity=2.0, unit="Unit", size="Large"),
        ),
        steps=("Simmer with the salt.",),
    )


def use_case(script) -> tuple[RecipeExtraction, FakeRecipeExtractor]:
    fake = FakeRecipeExtractor(script)
    return RecipeExtraction(fake, VOCABULARY), fake


def matching_draft() -> DraftRecipe:
    return DraftRecipe(
        title="Onion soup",
        base_servings=2,
        servings_estimated=False,
        main_ingredients=(),
        cuisines=(),
        ingredient_lines=(
            IngredientLine(
                name="onion",
                vague=False,
                quantity=2.0,
                unit="unit",
                size="large",
                text_name="onions",
                catalog_match="onion",
            ),
            IngredientLine(
                name="flour",
                vague=False,
                quantity=200.0,
                unit="g",
                text_name="flour",
                catalog_match="flour",
            ),
        ),
        steps=("Fry the onions.",),
    )


# ── acceptance (User Story 1) ───────────────────────────────────────────────


def test_acceptance_draft_is_checked_and_uses_catalog_name() -> None:
    service, fake = use_case(Draft(recipe=acceptance_draft()))

    result = service.extract(ACCEPTANCE_TEXT, ["onion"], 10.0)

    assert isinstance(result, Draft)
    recipe = result.recipe
    assert recipe.main_ingredients == ()
    assert recipe.cuisines == ("international",)
    assert recipe.base_servings == 4
    assert recipe.servings_estimated is True
    salt, onion = recipe.ingredient_lines
    assert salt.vague is True and salt.quantity is None and salt.unit is None
    assert onion.name == "onion"
    assert (onion.quantity, onion.unit, onion.size) == (2.0, "unit", "large")
    assert len(fake.calls) == 1


def test_draft_carries_matches_and_listed_changes_from_the_catalog() -> None:
    service, _ = use_case(Draft(recipe=matching_draft()))

    result = service.extract("Onion soup\n2 large onions\n200 g flour", ["onion", "flour"], 10.0)

    assert isinstance(result, Draft)
    recipe = result.recipe
    assert [match.kind for match in recipe.matches] == ["matched", "matched"]
    assert recipe.matches[0].entry == "onion"
    assert [line.name for line in recipe.ingredient_lines] == ["onion", "flour"]
    assert len(recipe.changes) == 1
    assert (recipe.changes[0].line, recipe.changes[0].from_name, recipe.changes[0].to) == (
        0,
        "onions",
        "onion",
    )


def test_draft_with_no_catalog_has_no_matches_and_no_changes() -> None:
    service, _ = use_case(Draft(recipe=matching_draft()))

    result = service.extract("Onion soup\n2 large onions\n200 g flour", [], 10.0)

    assert isinstance(result, Draft)
    assert [match.kind for match in result.recipe.matches] == ["new", "new"]
    assert result.recipe.changes == ()


def test_rule_breaking_draft_becomes_invalid_output_and_no_draft() -> None:
    broken = DraftRecipe(
        title="Soup",
        base_servings=0,
        servings_estimated=False,
        main_ingredients=(),
        cuisines=(),
        ingredient_lines=(IngredientLine(name="onion", vague=False, quantity=2.0, unit="unit"),),
        steps=("Stir.",),
    )
    service, _ = use_case(Draft(recipe=broken))

    assert isinstance(service.extract(ACCEPTANCE_TEXT, [], 10.0), InvalidOutput)


# ── incomplete drafts (User Story 1, FR-003) ────────────────────────────────


def test_missing_title_returns_draft_incomplete_naming_the_title() -> None:
    no_title = replace(acceptance_draft(), title="")
    service, _ = use_case(Draft(recipe=no_title))

    result = service.extract(ACCEPTANCE_TEXT, ["onion"], 10.0)

    assert isinstance(result, DraftIncomplete)
    assert result.problems.missing == ("title",)
    assert result.problems.line_problems == ()


def test_unit_missing_line_returns_draft_incomplete_with_the_line_problem() -> None:
    no_unit = DraftRecipe(
        title="Butter sauce",
        base_servings=None,
        servings_estimated=False,
        main_ingredients=(),
        cuisines=(),
        ingredient_lines=(IngredientLine(name="butter", vague=False, quantity=0.25),),
        steps=("Melt the butter.",),
    )
    service, _ = use_case(Draft(recipe=no_unit))

    result = service.extract(ACCEPTANCE_TEXT, [], 10.0)

    assert isinstance(result, DraftIncomplete)
    assert result.problems.line_problems == (
        LineProblem("butter", LineProblemKind.UNIT_MISSING),
    )


def test_incomplete_draft_log_names_kinds_only(caplog, monkeypatch: pytest.MonkeyPatch) -> None:
    # Alembic's fileConfig, run by the Postgres integration fixtures, disables
    # existing loggers for the rest of the session. Re-enable this one for log checks.
    monkeypatch.setattr(logging.getLogger("application.recipe_extraction"), "disabled", False)
    incomplete = DraftRecipe(
        title="Secret Title Soup",
        base_servings=None,
        servings_estimated=False,
        main_ingredients=(),
        cuisines=(),
        ingredient_lines=(IngredientLine(name="secretingredient", vague=False, quantity=2.0),),
        steps=("   ",),
    )
    service, _ = use_case(Draft(recipe=incomplete))

    with caplog.at_level(logging.WARNING, logger="application.recipe_extraction"):
        result = service.extract(ACCEPTANCE_TEXT, [], 10.0)

    assert isinstance(result, DraftIncomplete)
    assert "missing=steps" in caplog.text
    assert "line_problems=unit_missing" in caplog.text
    assert "secretingredient" not in caplog.text.lower()
    assert "secret title" not in caplog.text.lower()


# ── input refusal (FR-001, FR-012) ──────────────────────────────────────────


@pytest.mark.parametrize("text", ["", "   \n\t  "])
def test_empty_or_blank_text_is_refused_before_any_call(text: str) -> None:
    service, fake = use_case(Unavailable())

    with pytest.raises(RecipeTextRefusedError):
        service.extract(text, [], 10.0)
    assert fake.calls == []


def test_text_of_exactly_ten_thousand_characters_is_accepted() -> None:
    service, fake = use_case(NotARecipe(reason="Not a recipe."))

    result = service.extract("a" * MAX_TEXT_CHARS, [], 10.0)

    assert result == NotARecipe(reason="Not a recipe.")
    assert len(fake.calls) == 1


def test_text_of_ten_thousand_and_one_characters_is_refused() -> None:
    service, fake = use_case(Unavailable())

    with pytest.raises(RecipeTextRefusedError):
        service.extract("a" * (MAX_TEXT_CHARS + 1), [], 10.0)
    assert fake.calls == []


def test_length_is_counted_after_trimming_surrounding_spaces() -> None:
    service, _ = use_case(NotARecipe(reason="Not a recipe."))

    assert service.extract("   " + "a" * MAX_TEXT_CHARS + "   ", [], 10.0) == NotARecipe(
        reason="Not a recipe."
    )


def test_timeout_is_passed_through_to_the_port() -> None:
    service, fake = use_case(Unavailable())

    service.extract(ACCEPTANCE_TEXT, ["onion"], 10.0)

    assert fake.calls[0].timeout_s == 10.0
    assert fake.calls[0].ingredient_names == ("onion",)


# ── normal results and failures pass through unchanged (User Stories 2 and 3) ──


def test_not_a_recipe_passes_through_unchanged() -> None:
    weather = NotARecipe(reason="This is a question, not a recipe.")
    service, _ = use_case(weather)

    assert service.extract("What's the weather tomorrow?", [], 10.0) is weather


def test_two_recipes_reason_is_the_enum_and_not_a_failure() -> None:
    service, _ = use_case(NotARecipe(reason=NotRecipeReason.MULTIPLE_RECIPES))

    result = service.extract("Soup\n...\n\nCake\n...", [], 10.0)

    assert result == NotARecipe(reason=NotRecipeReason.MULTIPLE_RECIPES)


@pytest.mark.parametrize(
    "failure",
    [
        Unavailable(),
        LimitReached(retry_after_seconds=30),
        LimitReached(),
        InvalidOutput(),
        AIProviderError(),
    ],
)
def test_each_failure_class_passes_through_unchanged(failure) -> None:
    service, _ = use_case(failure)

    assert service.extract(ACCEPTANCE_TEXT, [], 10.0) == failure


# ── stand-in (User Story 5, SC-001) ─────────────────────────────────────────


def test_stand_in_returns_each_of_the_six_results_in_order() -> None:
    script = [
        Draft(recipe=acceptance_draft()),
        NotARecipe(reason="Not a recipe."),
        Unavailable(),
        LimitReached(retry_after_seconds=None),
        InvalidOutput(),
        AIProviderError(),
    ]
    fake = FakeRecipeExtractor(script)

    results = [fake.extract("text", [], 10.0) for _ in script]

    assert results == script
    assert len(fake.calls) == len(script)


def test_stand_in_returns_one_fixed_value_for_every_call() -> None:
    fake = FakeRecipeExtractor(Unavailable())

    assert fake.extract("a", [], 10.0) == Unavailable()
    assert fake.extract("b", [], 10.0) == Unavailable()


# ── concurrency (FR-016) ────────────────────────────────────────────────────


class _GatedExtractor:
    """Blocks inside the port until released, so a second caller can arrive mid-call."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = 0

    def extract(self, text, ingredient_names, timeout_s):
        self.calls += 1
        self.entered.set()
        self.release.wait(timeout=5)
        return NotARecipe(reason="Not a recipe.")


def test_concurrent_identical_texts_make_one_port_call_and_share_the_result() -> None:
    gate = _GatedExtractor()
    service = RecipeExtraction(gate, VOCABULARY)
    results: list[object] = []

    def call() -> None:
        results.append(service.extract(ACCEPTANCE_TEXT, [], 10.0))

    first = threading.Thread(target=call)
    first.start()
    assert gate.entered.wait(timeout=5)
    second = threading.Thread(target=call)
    second.start()
    time.sleep(0.05)
    gate.release.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert gate.calls == 1
    assert results == [NotARecipe(reason="Not a recipe."), NotARecipe(reason="Not a recipe.")]


def test_different_texts_make_separate_calls() -> None:
    service, fake = use_case(NotARecipe(reason="Not a recipe."))

    service.extract("first recipe", [], 10.0)
    service.extract("second recipe", [], 10.0)

    assert len(fake.calls) == 2


def test_in_flight_entry_is_removed_when_the_call_ends() -> None:
    service, _ = use_case(Unavailable())

    service.extract(ACCEPTANCE_TEXT, [], 10.0)

    assert service._in_flight == {}
