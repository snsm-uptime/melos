"""The shopping list in each viewer's language (spec 043 FR-007, FR-007a, FR-016). No database."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from api.schemas.shopping_list import closed_list_response, shopping_list_response
from application.shopping_list import ClosedListView, PlaceChoices, ShoppingListView
from domain.cart import Amount, MeasuredLine, RecipeRef, ShoppingList, YourCallEntry
from domain.places import PlaceRef
from domain.shopping_list import SavedLine, SavedList, cart_lines, line_names, stored_cart_list

SOUP = RecipeRef(uuid4(), "Soup")
NAMES = {
    "onion": {"en": "onion", "es": "cebolla"},
    "garlic": {"en": "garlic", "es": "ajo"},
}


def _built() -> ShoppingList:
    # Built lists are sorted by kept name: garlic, onion.
    return ShoppingList(
        lines=(
            MeasuredLine("garlic", "count", None, (Amount("2", "unit"),), (SOUP,)),
            MeasuredLine("onion", "count", None, (Amount("3", "unit"),), (SOUP,)),
        ),
        your_call=(YourCallEntry("salt", ("a pinch",), (SOUP,)),),
    )


def _view(language: str | None, places: PlaceChoices | None = None) -> ShoppingListView:
    return ShoppingListView(
        is_empty=False, shopping_list=_built(), names=NAMES, language=language, places=places
    )


def test_each_viewer_sees_their_word_on_one_line_sorted_by_it() -> None:
    english = shopping_list_response(_view("en"))
    spanish = shopping_list_response(_view("es"))
    assert [(ln.name, ln.kept_name) for ln in english.lines] == [
        ("garlic", "garlic"),
        ("onion", "onion"),
    ]
    # "ajo" sorts before "cebolla" for a Spanish viewer, as "garlic" before "onion" in English.
    assert [(ln.name, ln.kept_name) for ln in spanish.lines] == [
        ("ajo", "garlic"),
        ("cebolla", "onion"),
    ]
    assert spanish.lines[1].amounts[0].quantity == "3"
    # An ingredient with no variant shows its kept name.
    assert [e.name for e in spanish.your_call] == ["salt"]


def test_a_viewer_with_no_language_sees_kept_names() -> None:
    assert [ln.name for ln in shopping_list_response(_view(None)).lines] == ["garlic", "onion"]


def test_a_place_set_on_the_kept_name_applies_to_the_spanish_word() -> None:
    places = PlaceChoices({"onion": PlaceRef(key="farmers_market")}, ())
    line = next(
        ln for ln in shopping_list_response(_view("es", places)).lines if ln.name == "cebolla"
    )
    assert line.place is not None and line.place.key == "farmers_market"


def test_a_place_set_on_a_variant_applies_too() -> None:
    places = PlaceChoices({"ajo": PlaceRef(key="farmers_market")}, ())
    line = next(
        ln for ln in shopping_list_response(_view("en", places)).lines if ln.name == "garlic"
    )
    assert line.place is not None and line.place.key == "farmers_market"


def test_stored_lines_keep_their_words_and_hand_items_have_none() -> None:
    stored = cart_lines(_built(), NAMES)
    assert dict(stored[1].names) == {"en": "onion", "es": "cebolla"}
    assert stored[2].names == ()  # salt has no variant
    assert line_names(stored) == {"garlic": NAMES["garlic"], "onion": NAMES["onion"]}


def test_a_closed_list_shows_the_words_it_was_saved_with() -> None:
    items = tuple(
        SavedLine(
            line.origin,
            line.section,
            line.name,
            line.kind,
            line.size,
            line.amounts,
            line.notes,
            line.recipes,
            id=uuid4(),
            names=line.names,
        )
        for line in cart_lines(_built(), NAMES)
    )
    saved = SavedList(uuid4(), uuid4(), date(2026, 11, 6), datetime(2026, 11, 6, tzinfo=UTC), items)
    view = ClosedListView(saved, stored_cart_list(items), (), frozenset(), language="es")
    assert [ln.name for ln in closed_list_response(view).lines] == ["ajo", "cebolla"]
