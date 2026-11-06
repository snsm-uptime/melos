"""Pure tests for catalog management: merge, rename, split and pairs (spec 043). No database."""

from __future__ import annotations

import pytest
from domain.errors import (
    CatalogNameBlankError,
    CatalogNameChangedError,
    CatalogNameExistsError,
    CatalogNameOwnOtherError,
    CatalogNameUnknownError,
    SameIngredientError,
)
from domain.ingredient_catalog import (
    CatalogEntry,
    CatalogIndex,
    OtherName,
    check_rename,
    filter_pairs,
    normalize_new_name,
    plan_merge,
    split_plan,
)


def _index(*entries: CatalogEntry) -> CatalogIndex:
    return CatalogIndex.build(entries)


# --- plan_merge (T016, T017) --------------------------------------------------------------------


def test_a_spanish_name_merged_into_an_english_one_becomes_its_variant() -> None:
    index = _index(CatalogEntry("onion"), CatalogEntry("cebolla"))
    plan = plan_merge(index, "cebolla", "onion", "es", "en")
    assert plan.kept == "onion" and plan.merged == "cebolla"
    assert plan.kept_language == "en"
    assert plan.other_names == (OtherName("cebolla", "variant", "es"),)


def test_two_names_in_one_language_make_a_spelling() -> None:
    index = _index(CatalogEntry("scallion"), CatalogEntry("green onion"))
    plan = plan_merge(index, "green onion", "scallion", "en", "en")
    assert plan.other_names == (OtherName("green onion", "spelling"),)


def test_a_second_spanish_name_becomes_a_spelling() -> None:
    onion = CatalogEntry("onion", "en", {"es": "cebolla"})
    index = _index(onion, CatalogEntry("cebolleta"))
    plan = plan_merge(index, "cebolleta", "onion", "es", "en")
    assert plan.other_names == (OtherName("cebolleta", "spelling"),)


def test_the_kept_entry_keeps_its_own_language() -> None:
    index = _index(CatalogEntry("onion", "en"), CatalogEntry("cebolla"))
    plan = plan_merge(index, "cebolla", "onion", "es", "es")
    # "es" is not offered for "onion": its stored language wins, so "cebolla" stays a variant.
    assert plan.kept_language == "en"
    assert plan.other_names == (OtherName("cebolla", "variant", "es"),)


def test_the_merged_entry_s_other_names_come_along() -> None:
    cebolla = CatalogEntry("cebolla", "es", {"en": "yellow onion"}, ("cebollas moradas",))
    index = _index(CatalogEntry("onion"), cebolla)
    plan = plan_merge(index, "cebolla", "onion", "es", "en")
    assert plan.other_names == (
        OtherName("cebolla", "variant", "es"),
        # English is the kept language now, so the merged entry's English name is a spelling.
        OtherName("yellow onion", "spelling"),
        OtherName("cebollas moradas", "spelling"),
    )


def test_names_resolve_by_the_matching_rule() -> None:
    index = _index(CatalogEntry("onion"), CatalogEntry("cebolla"))
    assert plan_merge(index, "cebollas", "Onions", "es", "en").kept == "onion"


def test_merging_one_ingredient_with_itself_is_refused() -> None:
    onion = CatalogEntry("onion", "en", {"es": "cebolla"})
    with pytest.raises(SameIngredientError):
        plan_merge(_index(onion), "cebolla", "onion", "es", "en")


def test_an_unknown_name_is_refused() -> None:
    with pytest.raises(CatalogNameUnknownError):
        plan_merge(_index(CatalogEntry("onion")), "garlic", "onion", "en", "en")


# --- check_rename (T032) -------------------------------------------------------------------------


def test_a_rename_is_stored_normalized() -> None:
    index = _index(CatalogEntry("tomatoe"))
    assert check_rename(index, "tomatoe", "  Tomato ") == "tomato"
    assert normalize_new_name("Red  Peppers") == "red pepper"
    # Two possible singulars: kept as typed.
    assert normalize_new_name("potatoes") == "potatoes"


def test_a_rename_to_an_existing_name_offers_it() -> None:
    index = _index(CatalogEntry("tomatoe"), CatalogEntry("tomato"))
    with pytest.raises(CatalogNameExistsError) as raised:
        check_rename(index, "tomatoe", "tomatoes")
    assert raised.value.existing == "tomato"


def test_a_rename_to_another_ingredient_s_other_name_offers_that_ingredient() -> None:
    index = _index(CatalogEntry("onion", "en", {"es": "cebolla"}), CatalogEntry("ceboya"))
    with pytest.raises(CatalogNameExistsError) as raised:
        check_rename(index, "ceboya", "cebolla")
    assert raised.value.existing == "onion"


def test_a_rename_to_its_own_other_name_is_refused_without_a_merge_offer() -> None:
    index = _index(CatalogEntry("onion", "en", {"es": "cebolla"}))
    with pytest.raises(CatalogNameOwnOtherError):
        check_rename(index, "onion", "Cebolla")


def test_a_blank_name_is_refused() -> None:
    with pytest.raises(CatalogNameBlankError):
        check_rename(_index(CatalogEntry("onion")), "onion", "   ")


def test_a_name_that_is_gone_is_reported() -> None:
    with pytest.raises(CatalogNameChangedError):
        check_rename(_index(CatalogEntry("onion")), "garlic", "ajo")


def test_the_same_name_changes_nothing() -> None:
    assert check_rename(_index(CatalogEntry("onion")), "onion", "Onion") is None


# --- split_plan (T051) ---------------------------------------------------------------------------


def test_splitting_a_variant_moves_the_lines_of_its_language() -> None:
    onion = CatalogEntry("onion", "en", {"es": "cebolla"}, ("yellow onion",))
    plan = split_plan(onion, "cebolla")
    assert (plan.name, plan.language, plan.move_language) == ("cebolla", "es", "es")


def test_splitting_a_spelling_moves_no_line() -> None:
    onion = CatalogEntry("onion", "en", {"es": "cebolla"}, ("yellow onion",))
    plan = split_plan(onion, "yellow onion")
    assert (plan.name, plan.language, plan.move_language) == ("yellow onion", None, None)


def test_splitting_a_name_the_entry_lacks_is_reported() -> None:
    with pytest.raises(CatalogNameChangedError):
        split_plan(CatalogEntry("onion"), "cebolla")


# --- filter_pairs (T045) -------------------------------------------------------------------------


def test_only_real_undismissed_pairs_of_kept_names_are_kept() -> None:
    index = _index(
        CatalogEntry("garlic"),
        CatalogEntry("ajo"),
        CatalogEntry("flour"),
        CatalogEntry("harina"),
        CatalogEntry("onion", "en", {"es": "cebolla"}),
        CatalogEntry("salt"),
    )
    proposed = [
        ("garlic", "ajo"),
        ("Garlic", "Ajo"),  # repeated
        ("flour", "harina"),
        ("onion", "cebolla"),  # already one ingredient
        ("salt", "sal"),  # "sal" is not in the catalog
        ("pepper", "pimienta"),  # invented
    ]
    assert filter_pairs(index, [("harina", "flour")], proposed) == [("garlic", "ajo")]
