"""The Markdown copy of a list (spec 024 FR-004, research R3)."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from domain.cart import Amount, RecipeRef
from domain.shopping_export import build_export_document, render_markdown
from domain.shopping_list import SavedLine

DAY = date(2026, 11, 17)
A = RecipeRef(uuid4(), "Recipe A")
B = RecipeRef(uuid4(), "Recipe B")


def test_markdown_lists_lines_with_titles_manual_items_and_your_call() -> None:
    items = (
        SavedLine(
            "cart",
            "measured",
            "flour",
            "volume",
            None,
            (Amount("1", "cup"), Amount("3", "tbsp")),
            (),
            (A, B),
        ),
        SavedLine("hand", "measured", "lemon", None, None, (), (), ()),
        SavedLine("cart", "your_call", "salt", None, None, (), ("to taste",), (B,)),
    )
    text = render_markdown(build_export_document(items, DAY, "en"))
    assert text == (
        "## Shopping list (2026-11-17)\n"
        "\n"
        "- flour — 1 cup + 3 tbsp (Recipe A, Recipe B)\n"
        "- lemon (manual)\n"
        "\n"
        "## Your call\n"
        "\n"
        "- salt — to taste (Recipe B)\n"
    )


def test_an_empty_list_says_no_items_in_the_member_language() -> None:
    text = render_markdown(build_export_document((), DAY, "es"))
    assert text == "## Lista de compras (2026-11-17)\n\nSin artículos\n"


def test_numbers_keep_the_cart_formatting() -> None:
    items = (SavedLine("cart", "measured", "rice", "mass", None, (Amount("1.5", "kg"),), (), (A,)),)
    assert "- rice — 1.5 kg (Recipe A)" in render_markdown(build_export_document(items, DAY, "en"))
