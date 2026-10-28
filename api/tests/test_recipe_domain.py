"""Pure tests for the Save rules (spec 020 FR-005, FR-006, FR-007, FR-010)."""

from __future__ import annotations

import pytest
from domain.recipe import resolve_line_names
from domain.recipe_draft import (
    DraftProblems,
    DraftRecipe,
    IngredientLine,
    InvalidDraftError,
    check_edited_draft,
)


def _draft(
    lines: tuple[IngredientLine, ...] | None = None,
    *,
    title: str = "Onion soup",
    steps: tuple[str, ...] = ("Simmer them.",),
    servings: int | None = 4,
) -> DraftRecipe:
    if lines is None:
        lines = (IngredientLine(name="onion", vague=False, quantity=2, unit="unit"),)
    return DraftRecipe(
        title=title,
        base_servings=servings,
        servings_estimated=False,
        ingredient_lines=lines,
        steps=steps,
    )


def test_an_edited_draft_is_accepted_and_names_are_trimmed_and_lowered() -> None:
    draft = _draft(
        (IngredientLine(name="  Onion ", vague=False, quantity=2, unit="Unit", size="Large"),)
    )
    checked = check_edited_draft(draft)
    line = checked.ingredient_lines[0]
    assert (line.name, line.quantity, line.unit, line.size) == ("onion", 2.0, "unit", "large")
    assert checked.matches == () and checked.changes == ()


def test_the_estimated_flag_is_kept() -> None:
    draft = _draft()
    flagged = DraftRecipe(
        title=draft.title,
        base_servings=4,
        servings_estimated=True,
        ingredient_lines=draft.ingredient_lines,
        steps=draft.steps,
    )
    assert check_edited_draft(flagged).servings_estimated is True


def test_a_vague_line_keeps_its_note_and_has_no_amount() -> None:
    draft = _draft((IngredientLine(name="salt", vague=True, note="a pinch"),))
    line = check_edited_draft(draft).ingredient_lines[0]
    assert line.vague and line.note == "a pinch"
    assert line.quantity is None and line.unit is None


def test_missing_title_and_steps_are_collected() -> None:
    with pytest.raises(DraftProblems) as caught:
        check_edited_draft(_draft(title=" ", steps=()))
    assert set(caught.value.missing) == {"title", "steps"}


def test_a_line_with_no_unit_is_a_named_problem() -> None:
    draft = _draft((IngredientLine(name="flour", vague=False, quantity=1, unit=None),))
    with pytest.raises(DraftProblems) as caught:
        check_edited_draft(draft)
    assert caught.value.line_problems[0].name == "flour"


def test_a_vague_line_with_a_quantity_is_invalid() -> None:
    draft = _draft((IngredientLine(name="salt", vague=True, quantity=1, note="x"),))
    with pytest.raises(InvalidDraftError):
        check_edited_draft(draft)


def test_a_vague_line_without_a_note_is_invalid() -> None:
    draft = _draft((IngredientLine(name="salt", vague=True),))
    with pytest.raises(InvalidDraftError):
        check_edited_draft(draft)


def test_a_size_on_a_non_unit_line_is_dropped() -> None:
    line = IngredientLine(name="flour", vague=False, quantity=1, unit="cup", size="large")
    draft = _draft((line,))
    assert check_edited_draft(draft).ingredient_lines[0].size is None


def test_a_matching_name_takes_the_catalog_spelling() -> None:
    lines = (IngredientLine(name="onions", vague=False, quantity=1, unit="unit"),)
    resolved, new = resolve_line_names(lines, ["Onions "])
    assert resolved[0].name == "Onions " and new == ()


def test_letter_case_and_spacing_do_not_make_a_new_name() -> None:
    lines = (IngredientLine(name="red  pepper", vague=False, quantity=1, unit="unit"),)
    resolved, new = resolve_line_names(lines, ["red pepper"])
    assert resolved[0].name == "red pepper" and new == ()


def test_the_same_new_name_on_two_lines_is_listed_once() -> None:
    lines = (
        IngredientLine(name="leek", vague=False, quantity=1, unit="unit"),
        IngredientLine(name="leek", vague=True, note="some"),
    )
    resolved, new = resolve_line_names(lines, ["onion"])
    assert new == ("leek",) and [line.name for line in resolved] == ["leek", "leek"]


def test_an_empty_catalog_makes_every_distinct_name_new() -> None:
    lines = (
        IngredientLine(name="leek", vague=False, quantity=1, unit="unit"),
        IngredientLine(name="salt", vague=True, note="to taste"),
    )
    _, new = resolve_line_names(lines, [])
    assert new == ("leek", "salt")
