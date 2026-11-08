"""Pure tests for ingredient discovery (spec 073, T016). No database."""

from __future__ import annotations

from domain.ingredient_discovery import RecipeLineName, discover


def test_each_distinct_ingredient_is_found_once() -> None:
    lines = [
        RecipeLineName("onion", "en"),
        RecipeLineName("tomato", "en"),
        RecipeLineName("onion", "en"),
    ]
    assert [c.key for c in discover(lines)] == ["onion", "tomato"]


def test_plurals_case_and_spaces_are_one_candidate() -> None:
    lines = [
        RecipeLineName("Tomatoes", "en"),
        RecipeLineName("  tomato ", "en"),
        RecipeLineName("TOMATO", "en"),
    ]
    found = discover(lines)
    assert len(found) == 1
    assert found[0].key == "tomato"
    assert found[0].name == "Tomatoes"


def test_language_is_the_recipe_language() -> None:
    found = discover([RecipeLineName("cebolla", "es")])
    assert found[0].language == "es"


def test_first_seen_recipe_language_wins() -> None:
    lines = [RecipeLineName("garlic", "en"), RecipeLineName("ajo", "es")]
    found = discover(lines)
    assert [(c.key, c.language) for c in found] == [("garlic", "en"), ("ajo", "es")]


def test_blank_names_and_unsupported_languages_are_skipped() -> None:
    lines = [
        RecipeLineName("   ", "en"),
        RecipeLineName("salt", None),
        RecipeLineName("pepper", "fr"),
        RecipeLineName("basil", "en"),
    ]
    assert [c.key for c in discover(lines)] == ["basil"]


def test_no_lines_means_no_candidates() -> None:
    assert discover([]) == []
