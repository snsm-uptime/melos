"""Pure tests for ingredient catalog matching (spec 018, T010). No database."""

from __future__ import annotations

import time

import pytest
from domain.ingredient_catalog import (
    NEW,
    CatalogEntry,
    CatalogIndex,
    LineMatch,
    discovery_key,
    match_line,
    name_taken,
    names_to_add,
    normalize_name,
    propose_entry,
    same_spelling,
    shown_name,
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


# --- names_to_add: the merge when someone joins a notebook (spec 057) ---------------------


def test_merge_leaves_out_a_plural_of_a_notebook_name() -> None:
    assert names_to_add(["onions"], ["onion"]) == []


def test_merge_leaves_out_a_singular_of_a_notebook_plural() -> None:
    assert names_to_add(["onion"], ["onions"]) == []


def test_merge_adds_a_name_the_notebook_lacks() -> None:
    assert names_to_add(["saffron"], ["onion"]) == ["saffron"]


def test_merge_adds_one_of_two_forms_of_a_new_name() -> None:
    assert names_to_add(["tomatoes", "tomato"], []) == ["tomato"]


@pytest.mark.parametrize(
    ("incoming", "existing"),
    [("Azúcar", "azucar"), ("HARINA", "harina"), ("  sal  ", "sal"), ("JALAPEÑOS", "jalapeno")],
)
def test_merge_ignores_accents_case_and_spaces(incoming: str, existing: str) -> None:
    assert names_to_add([incoming], [existing]) == []


def test_merge_of_nothing_adds_nothing() -> None:
    assert names_to_add([], ["onion"]) == []
    assert names_to_add([], []) == []


def test_merge_skips_a_blank_name() -> None:
    assert names_to_add(["   "], []) == []


def test_merge_is_the_same_for_any_input_order() -> None:
    names = ["tomatoes", "saffron", "tomato", "leaves", "leaf"]
    assert names_to_add(names, []) == names_to_add(list(reversed(names)), [])


SAMPLE = [
    "onion", "onions", "tomato", "tomatoes", "berry", "berries", "leaf", "leaves", "knife",
    "knives", "bay leaves", "bay leaf", "azúcar", "AZUCAR", "pasta", "pastas", "garlic", "couscous",
    "hummus", "glass", "peach", "peaches", "limón", "limones", "pan", "panes", "pie", "pies", "sal",
    "sales", "aji", "ajis", "cheese", "cheeses", "bus", "gas", "harina de maíz", "harina de maiz",
]  # fmt: skip


@pytest.mark.parametrize("existing", [[], ["onion", "pies"], SAMPLE[::2], SAMPLE[1::3]])
def test_merge_agrees_with_match_line(existing: list[str]) -> None:
    """Each name left out matches something known; each name added matches nothing known."""
    added = names_to_add(SAMPLE, existing)
    assert len(added) == len(set(added))
    for name in SAMPLE:
        known = [*existing, *added]
        matches = propose_entry(name, known) is not None
        assert matches, f"{name} should match {known}"
    for index, name in enumerate(added):
        others = [*existing, *added[:index]]
        assert propose_entry(name, others) is None, f"{name} matched {others}"


def test_merge_of_500_by_500_names_is_quick() -> None:
    incoming = [f"name{index}x" for index in range(500)]
    existing = [f"name{index}y" for index in range(500)]
    started = time.perf_counter()
    assert len(names_to_add(incoming, existing)) == 500
    assert time.perf_counter() - started < 2


# --- spec 043: other names ------------------------------------------------------------------

ONION = CatalogEntry(
    name="onion", language="en", variants={"es": "cebolla"}, spellings=("yellow onion",)
)
INDEX = CatalogIndex.build([ONION, CatalogEntry(name="garlic")])


def test_a_plural_of_a_variant_matches_its_ingredient() -> None:
    match = match_line("cebollas", "cebollas", "cebolla", INDEX)
    assert match == LineMatch(kind="matched", entry="onion")
    assert INDEX.kept_for("Cebollas") == "onion"


def test_a_spelling_matches_its_ingredient() -> None:
    assert match_line(None, "yellow onions", "yellow onion", INDEX).entry == "onion"
    assert propose_entry("yellow onions", INDEX) == "onion"


def test_shown_name_by_language() -> None:
    plain = CatalogEntry(name="garlic")
    assert shown_name(plain, "es") == "garlic"
    assert shown_name(ONION, "en") == "onion"
    assert shown_name(ONION, "es") == "cebolla"
    assert shown_name(ONION, None) == "onion"
    no_spanish = CatalogEntry(name="flour", language="en")
    assert shown_name(no_spanish, "es") == "flour"


def test_names_to_add_skips_other_names() -> None:
    assert names_to_add(["cebollas", "tomato", "garlic"], INDEX) == ["tomato"]


def test_name_taken_covers_kept_and_other_names() -> None:
    assert name_taken(INDEX, "Cebolla")
    assert name_taken(INDEX, "garlic")
    assert not name_taken(INDEX, "tomato")


def test_a_plain_index_answers_like_a_list_of_names() -> None:
    names = ["tomato", "red pepper"]
    plain = CatalogIndex.of_names(names)
    assert not plain.has_other_names()
    for text in ("tomatoes", "Red Peppers", "basil"):
        assert propose_entry(text, plain) == propose_entry(text, names)
        assert match_line(None, text, "tomato", plain) == match_line(None, text, "tomato", names)


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("Onions", "onion"),
        ("  onion ", "onion"),
        ("Tomatoes", "tomato"),
        ("Berries", "berry"),
        ("Leaves", "leaf"),
        ("Cebollas", "cebolla"),
        ("limón", "limon"),
        ("limones", "limon"),
        ("LIMON", "limon"),
    ],
)
def test_discovery_key_joins_plurals_case_and_spaces(text: str, key: str) -> None:
    assert discovery_key(text) == key
