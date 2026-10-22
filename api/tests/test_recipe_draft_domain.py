"""Domain tests for the recipe draft rules (FR-006 to FR-006c, SC-003). Pure pytest, no I/O."""

from __future__ import annotations

from pathlib import Path

import pytest
from adapters.llm.vocabulary import VOCABULARY_DIR, load_vocabulary
from domain.recipe_draft import (
    DraftRecipe,
    IngredientLine,
    InvalidDraftError,
    check_draft,
    lookup_unit,
    score_cuisines,
)

VOCABULARY = load_vocabulary()


def check(recipe: DraftRecipe, catalog: list[str]) -> DraftRecipe:
    return check_draft(recipe, catalog, VOCABULARY)


def cuisines(title: str, steps: list[str], line_count: int) -> tuple[str, ...]:
    return score_cuisines(title, steps, line_count, VOCABULARY)


CATALOG = ["onion", "flour"]


def draft(
    *,
    title: str = "Onion soup",
    base_servings: int | None = 4,
    main_ingredients: tuple[str, ...] = (),
    lines: tuple[IngredientLine, ...] | None = None,
    steps: tuple[str, ...] = ("Simmer the onion.",),
) -> DraftRecipe:
    if lines is None:
        lines = (
            IngredientLine("salt", True, note="a pinch of"),
            IngredientLine("onion", False, 2.0, "unit", "large"),
        )
    return DraftRecipe(
        title=title,
        base_servings=base_servings,
        servings_estimated=False,
        main_ingredients=main_ingredients,
        cuisines=(),
        ingredient_lines=lines,
        steps=steps,
    )


def line(**overrides) -> IngredientLine:
    values = {"name": "flour", "vague": False, "quantity": 1.0, "unit": "cup"}
    values.update(overrides)
    return IngredientLine(**values)


# ── units (FR-006a) ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Tablespoon", "tbsp"),
        ("  cucharadas  ", "tbsp"),
        ("tbs", "tbsp"),
        ("cups.", "cup"),
        ("libra", "lb"),
        ("Unit", "unit"),
        ("tablespon", "tbsp"),
        ("cupss", "cup"),
        ("gramz", "g"),
    ],
)
def test_known_and_one_edit_units_map_to_allowed_unit(raw: str, expected: str) -> None:
    assert lookup_unit(raw) == expected


@pytest.mark.parametrize("raw", ["quart", "pint", "fl oz", "stick", "vaso", "tspn", ""])
def test_unknown_or_conversion_units_have_no_match(raw: str) -> None:
    assert lookup_unit(raw) is None


def test_five_char_unit_one_edit_from_two_units_is_invalid_output() -> None:
    with pytest.raises(InvalidDraftError):
        lookup_unit("cdaas")


# ── lines (FR-006, FR-006c) ─────────────────────────────────────────────────


def test_non_vague_line_maps_unit_and_keeps_quantity_unconverted() -> None:
    checked = check(draft(lines=(line(unit="tablespoon", quantity=3.0),)), CATALOG)
    kept = checked.ingredient_lines[0]
    assert kept.unit == "tbsp"
    assert kept.quantity == 3.0


@pytest.mark.parametrize("quantity", [None, 0, -1, float("nan")])
def test_non_vague_line_needs_a_positive_quantity(quantity) -> None:
    with pytest.raises(InvalidDraftError):
        check(draft(lines=(line(quantity=quantity),)), CATALOG)


def test_non_vague_line_needs_a_unit() -> None:
    with pytest.raises(InvalidDraftError):
        check(draft(lines=(line(unit=""),)), CATALOG)


def test_non_vague_line_with_unknown_unit_is_invalid_output() -> None:
    with pytest.raises(InvalidDraftError):
        check(draft(lines=(line(unit="quart"),)), CATALOG)


def test_vague_line_has_no_quantity_and_no_unit() -> None:
    with pytest.raises(InvalidDraftError):
        check(draft(lines=(line(vague=True, quantity=1.0, unit=None),)), CATALOG)
    with pytest.raises(InvalidDraftError):
        check(draft(lines=(line(vague=True, quantity=None, unit="cup"),)), CATALOG)


def test_vague_line_keeps_its_note() -> None:
    checked = check(
        draft(lines=(IngredientLine("salt", True, note=" to taste ", size="large"),)), CATALOG
    )
    assert checked.ingredient_lines[0].note == "to taste"
    assert checked.ingredient_lines[0].size is None


def test_size_only_with_unit_unit() -> None:
    checked = check(draft(lines=(line(unit="cup", size="large"),)), CATALOG)
    assert checked.ingredient_lines[0].size is None


def test_size_outside_small_medium_large_is_removed_and_line_kept() -> None:
    checked = check(draft(lines=(line(unit="unit", size="huge"),)), CATALOG)
    assert checked.ingredient_lines[0].size is None
    assert checked.ingredient_lines[0].quantity == 1.0


def test_size_is_kept_for_unit_with_allowed_size() -> None:
    checked = check(draft(lines=(line(unit="unit", size="Medium"),)), CATALOG)
    assert checked.ingredient_lines[0].size == "medium"


def test_name_is_lower_case_and_uses_catalog_spelling() -> None:
    checked = check(draft(lines=(line(name="  ONION ", unit="unit"),)), ["Onion"])
    assert checked.ingredient_lines[0].name == "Onion"
    unknown = check(draft(lines=(line(name="Basil", unit="unit"),)), CATALOG)
    assert unknown.ingredient_lines[0].name == "basil"


def test_empty_name_is_invalid_output() -> None:
    with pytest.raises(InvalidDraftError):
        check(draft(lines=(line(name="   "),)), CATALOG)


# ── draft rules (FR-006b) ───────────────────────────────────────────────────


def test_title_must_not_be_blank() -> None:
    with pytest.raises(InvalidDraftError):
        check(draft(title="   "), CATALOG)


def test_title_limit_is_200_characters() -> None:
    assert check(draft(title="x" * 200), CATALOG).title == "x" * 200
    with pytest.raises(InvalidDraftError):
        check(draft(title="x" * 201), CATALOG)


def test_at_least_one_step_is_required() -> None:
    with pytest.raises(InvalidDraftError):
        check(draft(steps=()), CATALOG)
    with pytest.raises(InvalidDraftError):
        check(draft(steps=("  ", "")), CATALOG)


def test_missing_servings_default_to_four_and_are_estimated() -> None:
    checked = check(draft(base_servings=None), CATALOG)
    assert checked.base_servings == 4
    assert checked.servings_estimated is True


def test_given_servings_are_kept_and_not_estimated() -> None:
    checked = check(draft(base_servings=2), CATALOG)
    assert checked.base_servings == 2
    assert checked.servings_estimated is False


def test_servings_below_one_are_invalid_output() -> None:
    with pytest.raises(InvalidDraftError):
        check(draft(base_servings=0), CATALOG)


# ── categories (FR-006) ─────────────────────────────────────────────────────


def test_main_ingredients_keep_only_listed_keys_and_at_most_two() -> None:
    checked = check(
        draft(main_ingredients=("chicken", "poultry", "beef", "fish", "garlic")), CATALOG
    )
    assert checked.main_ingredients == ("poultry", "beef")


def test_zero_main_ingredients_is_allowed() -> None:
    checked = check(draft(main_ingredients=("garlic",)), CATALOG)
    assert checked.main_ingredients == ()


def test_no_cuisine_match_gives_international() -> None:
    checked = check(draft(title="Onion soup", steps=("Stir.",)), CATALOG)
    assert checked.cuisines == ("international",)


def test_cuisine_matches_by_title_coverage() -> None:
    assert cuisines("Moroccan tagine", ["Cook."], 2) == ("moroccan",)


def test_cuisine_steps_rule_is_off_below_five_lines() -> None:
    steps = ["Add the garlic, cumin, turmeric, garam masala, ginger and chili."]
    assert cuisines("Lentil stew", steps, 4) == ("international",)
    assert cuisines("Lentil stew", steps, 6) == ("indian",)


def test_cuisines_are_at_most_two_and_one_per_tag() -> None:
    result = cuisines("Ethiopian Moroccan fusion", ["Cook."], 2)
    assert len(result) <= 2
    assert len(set(result)) == len(result)


# ── vocabulary copies (Assumptions: category lists) ─────────────────────────


@pytest.mark.parametrize("name", ["categories.yaml", "cuisine.yml"])
def test_vocabulary_copies_in_domain_match_dev_docs(name: str) -> None:
    source = Path(__file__).resolve().parents[2] / "dev" / "docs" / name
    if not source.exists():
        pytest.skip("dev/docs is not in the container image")
    assert (VOCABULARY_DIR / name).read_bytes() == source.read_bytes()
