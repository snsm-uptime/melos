"""Domain tests for the recipe draft rules (FR-006 to FR-006c, SC-003). Pure pytest, no I/O."""

from __future__ import annotations

from pathlib import Path

import pytest
from adapters.llm.vocabulary import VOCABULARY_DIR, load_vocabulary
from domain.recipe_draft import (
    DraftProblems,
    DraftRecipe,
    IngredientLine,
    InvalidDraftError,
    LineProblem,
    LineProblemKind,
    check_draft,
    clean_display_name,
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
        ("dientes de ajo", "unit"),
        ("Diente de ajo", "unit"),
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
    with pytest.raises(DraftProblems):
        check(draft(lines=(line(quantity=quantity),)), CATALOG)


def test_non_vague_line_needs_a_unit() -> None:
    with pytest.raises(DraftProblems):
        check(draft(lines=(line(unit=""),)), CATALOG)


def test_non_vague_line_with_unknown_unit_is_a_named_problem() -> None:
    with pytest.raises(DraftProblems):
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


def test_name_is_lower_case_without_a_proposal() -> None:
    checked = check(draft(lines=(line(name="  ONION ", unit="unit"),)), ["Onion"])
    assert checked.ingredient_lines[0].name == "onion"
    assert checked.matches[0].kind == "new"
    unknown = check(draft(lines=(line(name="Basil", unit="unit"),)), CATALOG)
    assert unknown.ingredient_lines[0].name == "basil"


def test_matched_line_shows_the_catalog_entry_and_lists_the_change() -> None:
    raw = draft(lines=(line(name="onion", unit="unit", text_name="onions", catalog_match="onion"),))
    checked = check(raw, ["onion"])
    assert checked.ingredient_lines[0].name == "onion"
    assert checked.matches[0].kind == "matched"
    assert checked.changes[0].from_name == "onions"
    assert checked.changes[0].to == "onion"
    assert checked.ingredient_lines[0].text_name == "onions"


def test_text_name_falls_back_to_the_assistant_name_when_missing() -> None:
    checked = check(draft(lines=(line(name="Flour", unit="g", quantity=200.0),)), CATALOG)

    assert checked.ingredient_lines[0].text_name == "flour"


def test_empty_name_is_invalid_output() -> None:
    with pytest.raises(InvalidDraftError):
        check(draft(lines=(line(name="   "),)), CATALOG)


# ── draft rules (FR-006b) ───────────────────────────────────────────────────


def test_title_must_not_be_blank() -> None:
    with pytest.raises(DraftProblems):
        check(draft(title="   "), CATALOG)


def test_title_limit_is_200_characters() -> None:
    assert check(draft(title="x" * 200), CATALOG).title == "x" * 200
    with pytest.raises(InvalidDraftError):
        check(draft(title="x" * 201), CATALOG)


def test_at_least_one_step_is_required() -> None:
    with pytest.raises(DraftProblems):
        check(draft(steps=()), CATALOG)
    with pytest.raises(DraftProblems):
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


# ── steps rule boundary and vocabulary copies (FR-006, Assumptions) ─────────


def _node_aliases(cuisine_id: str, count: int) -> list[str]:
    """Distinct ingredient aliases, each naming one ingredient of the cuisine node."""
    node = next(n for n in VOCABULARY.cuisine_nodes if n.id == cuisine_id)
    picked: list[str] = []
    used_ids: set[str] = set()
    for alias, ids in VOCABULARY.matching.ingredient_items:
        if len(alias) < 4 or len(ids) != 1 or ids[0] not in node.ingredient_ids:
            continue
        if ids[0] in used_ids or any(alias in other or other in alias for other in picked):
            continue
        picked.append(alias)
        used_ids.add(ids[0])
        if len(picked) == count:
            return picked
    raise AssertionError(f"{cuisine_id} has fewer than {count} distinct ingredient aliases")


def test_cuisine_steps_rule_does_not_match_at_three_ingredients() -> None:
    three = _node_aliases("mexican", 3)
    assert cuisines("Zzqx plate", [", ".join(three) + "."], 5) == ("international",)


def test_cuisine_steps_rule_matches_at_four_ingredients() -> None:
    four = _node_aliases("mexican", 4)
    assert "mexican" in cuisines("Zzqx plate", [", ".join(four) + "."], 5)


def test_preparation_is_trimmed_and_blank_becomes_none() -> None:
    checked = check(
        draft(lines=(line(preparation="  chopped  "), line(name="onion", preparation="   "))),
        CATALOG,
    )

    assert checked.ingredient_lines[0].preparation == "chopped"
    assert checked.ingredient_lines[1].preparation is None


# ── display names ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("butter", "butter"),
        ("  crème fraîche ", "crème fraîche"),
        ("o'neil-style", "o'neil-style"),
        ("Ñoquis  de   papa", "Ñoquis de papa"),
        ("a" * 40, "a" * 40),
    ],
)
def test_clean_display_name_keeps_letters_spaces_hyphens_and_apostrophes(
    raw: str, expected: str
) -> None:
    assert clean_display_name(raw) == expected


@pytest.mark.parametrize("raw", ["2 x butter!", "butter.", "salt & pepper", "a" * 41])
def test_clean_display_name_refuses_digits_punctuation_and_long_names(raw: str) -> None:
    assert clean_display_name(raw) is None


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_clean_display_name_refuses_empty_input(raw: str | None) -> None:
    assert clean_display_name(raw) is None


@pytest.mark.parametrize("name", ["categories.yaml", "cuisine.yml"])
def test_vocabulary_copies_in_domain_match_dev_docs(name: str) -> None:
    source = Path(__file__).resolve().parents[2] / "dev" / "docs" / name
    if not source.exists():
        pytest.skip("dev/docs is not in the container image")
    assert (VOCABULARY_DIR / name).read_bytes() == source.read_bytes()


# ── missing parts and line problems (User Story 1, FR-003) ──────────────────


def problems_of(recipe: DraftRecipe) -> DraftProblems:
    with pytest.raises(DraftProblems) as raised:
        check(recipe, CATALOG)
    return raised.value


def test_empty_title_is_a_missing_title() -> None:
    assert problems_of(draft(title="  ")).missing == ("title",)


def test_no_non_blank_step_is_a_missing_steps() -> None:
    assert problems_of(draft(steps=("  ", ""))).missing == ("steps",)


def test_missing_title_and_steps_are_both_named_in_order() -> None:
    assert problems_of(draft(title="", steps=())).missing == ("title", "steps")


def test_empty_ingredient_list_gives_no_problems() -> None:
    checked = check(draft(lines=()), CATALOG)
    assert checked.ingredient_lines == ()


def test_no_quantity_is_quantity_missing() -> None:
    problems = problems_of(draft(lines=(line(quantity=None),)))
    assert problems.line_problems == (LineProblem("flour", LineProblemKind.QUANTITY_MISSING),)


@pytest.mark.parametrize("quantity", [0, -1])
def test_zero_or_negative_quantity_is_quantity_missing(quantity) -> None:
    problems = problems_of(draft(lines=(line(quantity=quantity),)))
    assert problems.line_problems == (LineProblem("flour", LineProblemKind.QUANTITY_MISSING),)


def test_no_unit_is_unit_missing() -> None:
    problems = problems_of(draft(lines=(line(unit=""),)))
    assert problems.line_problems == (LineProblem("flour", LineProblemKind.UNIT_MISSING),)


def test_unknown_unit_is_unit_not_recognized() -> None:
    problems = problems_of(draft(lines=(line(unit="widgets"),)))
    assert problems.line_problems == (
        LineProblem("flour", LineProblemKind.UNIT_NOT_RECOGNIZED),
    )


def test_line_with_neither_quantity_nor_unit_gives_two_entries_with_one_name() -> None:
    problems = problems_of(draft(lines=(line(quantity=None, unit=""),)))
    assert problems.line_problems == (
        LineProblem("flour", LineProblemKind.QUANTITY_MISSING),
        LineProblem("flour", LineProblemKind.UNIT_MISSING),
    )


def test_line_problem_name_is_the_normalized_ingredient_name() -> None:
    problems = problems_of(draft(lines=(line(name="Butter", quantity=0.25, unit=""),)))
    assert problems.line_problems == (LineProblem("butter", LineProblemKind.UNIT_MISSING),)


def test_vague_line_without_amount_is_never_a_line_problem() -> None:
    checked = check(draft(lines=(IngredientLine("salt", True, note="a pinch of"),)), CATALOG)
    assert checked.ingredient_lines[0].vague is True


def test_missing_title_and_a_bad_line_are_both_returned_in_one_refusal() -> None:
    problems = problems_of(draft(title="", lines=(line(unit=""),)))
    assert problems.missing == ("title",)
    assert problems.line_problems == (LineProblem("flour", LineProblemKind.UNIT_MISSING),)


def test_missing_servings_with_no_named_problem_is_still_invalid_draft() -> None:
    with pytest.raises(InvalidDraftError):
        check(draft(base_servings=0), CATALOG)


def test_servings_below_one_with_a_named_problem_is_draft_problems() -> None:
    with pytest.raises(DraftProblems):
        check(draft(base_servings=0, title=""), CATALOG)
