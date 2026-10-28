"""Pure tests for ingredient catalog matching (spec 018, T010). No database."""

from __future__ import annotations

import pytest
from domain.ingredient_catalog import (
    NEW,
    LineMatch,
    match_line,
    normalize_name,
    same_spelling,
    singular_forms,
)

CATALOG = ["onion", "flour", "tomato", "berry", "leaf", "cebolla", "limon"]


@pytest.mark.parametrize(
    ("text_name", "entry"),
    [
        ("onions", "onion"),
        ("tomatoes", "tomato"),
        ("berries", "berry"),
        ("leaves", "leaf"),
        ("cebollas", "cebolla"),
        ("limones", "limon"),
        ("onion", "onion"),
    ],
)
def test_plural_and_singular_forms_match(text_name: str, entry: str) -> None:
    assert match_line(text_name, text_name, entry, CATALOG) == LineMatch("matched", entry)


def test_accent_is_ignored_when_comparing() -> None:
    assert match_line("limón", "limón", "limon", CATALOG) == LineMatch("matched", "limon")


def test_letter_case_and_spaces_are_ignored() -> None:
    assert match_line("Onion", "Onion", "onion", CATALOG) == LineMatch("matched", "onion")
    assert normalize_name("  Red   Onion ") == "red onion"


def test_proposal_not_in_catalog_is_rejected() -> None:
    assert match_line("onions", "onions", "shallot", CATALOG) == NEW


def test_no_proposal_is_new() -> None:
    assert match_line("onions", "onions", None, CATALOG) == NEW


def test_proposal_that_does_not_match_the_line_is_rejected() -> None:
    assert match_line("flour", "flour", "onion", CATALOG) == NEW


def test_empty_catalog_is_new() -> None:
    assert match_line("onions", "onions", "onion", []) == NEW


def test_text_name_wins_over_assistant_name_when_present() -> None:
    assert match_line("onions", "onion", "onion", CATALOG) == LineMatch("matched", "onion")


def test_falls_back_to_name_when_text_name_is_missing() -> None:
    assert match_line(None, "onions", "onion", CATALOG) == LineMatch("matched", "onion")


def test_proposal_wins_between_entries_that_normalize_the_same() -> None:
    catalog = ["onion", "onions"]

    assert match_line("onions", "onions", "onions", catalog) == LineMatch("matched", "onions")
    assert match_line("onions", "onions", "onion", catalog) == LineMatch("matched", "onion")


def test_proposal_must_be_an_exact_catalog_entry() -> None:
    assert match_line("onions", "onions", "Onion", ["onion"]) == NEW


def test_same_spelling_ignores_case_and_spaces_only() -> None:
    assert same_spelling("Onion", "onion")
    assert same_spelling("red  onion", "red onion")
    assert not same_spelling("onions", "onion")
    assert not same_spelling("limón", "limon")


def test_singular_forms_follow_english_and_spanish_rules() -> None:
    assert "berry" in singular_forms("berries")
    assert "tomato" in singular_forms("tomatoes")
    assert "dish" in singular_forms("dishes")
    assert "cebolla" in singular_forms("cebollas")
    assert "limon" in singular_forms("limones")


def test_multi_word_names_singularize_their_last_word() -> None:
    assert match_line("bay leaves", "bay leaves", "bay leaf", ["bay leaf"]) == LineMatch(
        "matched", "bay leaf"
    )
    assert "red onion" in singular_forms("red onions")


def test_short_words_are_not_singularized() -> None:
    assert singular_forms("gas") == frozenset({"gas"})
    assert singular_forms("rice") == frozenset({"rice"})
