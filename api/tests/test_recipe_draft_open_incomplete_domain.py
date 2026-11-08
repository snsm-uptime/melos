"""open_incomplete: the draft of a partial read, shared by link and picture capture (spec 041)."""

from __future__ import annotations

from domain.recipe_draft import DEFAULT_SERVINGS, DraftRecipe, IngredientLine, open_incomplete


def _line(name: str) -> IngredientLine:
    return IngredientLine(name=name, vague=False)


def _draft(**overrides: object) -> DraftRecipe:
    fields: dict[str, object] = {
        "title": "Tomato soup",
        "base_servings": 4,
        "servings_estimated": False,
        "ingredient_lines": (_line("tomato"),),
        "steps": ("Blend.",),
        "language": None,
    }
    fields.update(overrides)
    return DraftRecipe(**fields)  # type: ignore[arg-type]


def test_blank_title_stays_blank_and_a_title_is_trimmed() -> None:
    assert open_incomplete(_draft(title="")).title == ""
    assert open_incomplete(_draft(title="   ")).title == ""
    assert open_incomplete(_draft(title="  Soup  ")).title == "Soup"


def test_drops_empty_steps_and_strips_the_rest() -> None:
    result = open_incomplete(_draft(steps=("  Chop.  ", "", "   ", "Stir.")))
    assert result.steps == ("Chop.", "Stir.")


def test_keeps_ingredient_lines_exactly_as_given() -> None:
    lines = (_line("tomato"), _line("  salt  "))
    assert open_incomplete(_draft(ingredient_lines=lines)).ingredient_lines == lines


def test_servings_below_one_or_missing_become_the_default_and_are_estimated() -> None:
    for servings in (None, 0, -2):
        result = open_incomplete(_draft(base_servings=servings))
        assert result.base_servings == DEFAULT_SERVINGS
        assert result.servings_estimated is True


def test_a_valid_servings_count_is_kept_and_not_estimated() -> None:
    result = open_incomplete(_draft(base_servings=6))
    assert result.base_servings == 6
    assert result.servings_estimated is False


def test_keeps_the_language() -> None:
    assert open_incomplete(_draft(language="es")).language == "es"
    assert open_incomplete(_draft(language=None)).language is None


def test_never_matches_lines_to_the_catalog() -> None:
    assert open_incomplete(_draft()).matches == ()
