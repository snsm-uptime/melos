"""The export document: order, sources, manual items and empty lists (spec 024)."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from domain.cart import Amount, RecipeRef
from domain.shopping_export import build_export_document
from domain.shopping_list import SavedLine

DAY = date(2026, 11, 17)
A = RecipeRef(uuid4(), "Recipe A")
B = RecipeRef(uuid4(), "Recipe B")


def cart_line(name: str, amounts: tuple[Amount, ...], recipes: tuple[RecipeRef, ...]) -> SavedLine:
    return SavedLine("cart", "measured", name, "volume", None, amounts, (), recipes)


def test_measured_lines_come_before_your_call_and_keep_their_order() -> None:
    items = (
        cart_line("flour", (Amount("1", "cup"),), (A,)),
        SavedLine("cart", "your_call", "salt", None, None, (), ("to taste",), (B,)),
        cart_line("milk", (Amount("2", "cup"),), (B,)),
    )
    document = build_export_document(items, DAY, "en")
    assert [line.text for line in document.lines] == ["flour — 1 cup", "milk — 2 cup"]
    assert [line.text for line in document.your_call] == ["salt — to taste"]


def test_sources_are_the_recipe_titles_and_a_manual_item_has_none() -> None:
    items = (
        cart_line("flour", (Amount("1", "cup"), Amount("3", "tbsp")), (A, B)),
        SavedLine("hand", "measured", "lemon", None, None, (), (), ()),
    )
    document = build_export_document(items, DAY, "en")
    assert document.lines[0].sources == ("Recipe A", "Recipe B")
    assert document.lines[0].text == "flour — 1 cup + 3 tbsp"
    assert document.lines[1].is_manual is True
    assert document.lines[1].sources == ()


def test_a_count_shows_its_number_and_a_size_is_part_of_the_name() -> None:
    items = (
        SavedLine("cart", "measured", "egg", "count", "large", (Amount("2", "unit"),), (), (A,)),
    )
    document = build_export_document(items, DAY, "es")
    assert document.lines[0].text == "egg, large — 2"


def test_an_empty_list_gives_empty_sections() -> None:
    document = build_export_document((), DAY, "en")
    assert document.lines == ()
    assert document.your_call == ()
    assert document.list_date == DAY
