"""The lists the draft editor shows (spec 016 FR-011; GET /recipe-vocabulary).

Pure: it shapes the units, sizes and paste limit and does no I/O. The main ingredient and
cuisine lists are out of the MVP (S-061); their code is commented out under MVP-OUT.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from domain.recipe_draft import (
    ALLOWED_UNITS,
    SIZES,
    InvalidDraftError,
    custom_unit_name,
    lookup_unit,
)

# MVP-OUT: also imported Mapping, MAX_CUISINES and MAX_MAIN_INGREDIENTS


# MVP-OUT: main ingredients and cuisines are out of the MVP (S-061); restore from here
# def _tag_of(cuisines: Mapping[str, Any], cuisine_id: str) -> str:
#     """The nearest tag on the primary parent chain, the node itself when it is a tag."""
#     current_id = cuisine_id
#     current = cuisines[current_id]
#     while current.get("role") != "tag" and current.get("parents"):
#         current_id = current["parents"][0]
#         current = cuisines[current_id]
#     return current_id


# MVP-OUT: the original answer with the main ingredient and cuisine lists
# def vocabulary_answer(
#     categories: Mapping[str, Any],
#     cuisine: Mapping[str, Any],
#     *,
#     max_text_chars: int,
# ) -> dict[str, Any]:
#     main_values = categories["categories"]["main_ingredient"]["values"]
#     cuisines = cuisine["cuisines"]
#
#     listed: list[dict[str, Any]] = []
#     for cuisine_id, node in cuisines.items():
#         if node.get("kind") == "fallback":
#             listed.append({"id": cuisine_id, "label": node["label"], "tag": None})
#         elif node.get("role") == "tag":
#             listed.append({"id": cuisine_id, "label": node["label"], "tag": None})
#         elif node.get("role") == "variant":
#             tag = _tag_of(cuisines, cuisine_id)
#             listed.append({"id": cuisine_id, "label": node["label"], "tag": tag})
#
#     return {
#         "units": list(ALLOWED_UNITS),
#         "sizes": list(SIZES),
#         "max_main_ingredients": MAX_MAIN_INGREDIENTS,
#         "max_cuisines": MAX_CUISINES,
#         "max_text_chars": max_text_chars,
#         "main_ingredients": [
#             {"id": key, "label": value["label"]} for key, value in main_values.items()
#         ],
#         "cuisines": listed,
#     }


@dataclass(frozen=True, slots=True)
class UnitCheck:
    outcome: Literal["known", "new", "not_a_unit"]
    unit: str | None


def check_unit_word(word: str, available: Sequence[str]) -> UnitCheck:
    """A word typed by hand: `known` gives the unit for the line, `new` needs the question (R12)."""
    try:
        known = lookup_unit(word, available)
    except InvalidDraftError:
        return UnitCheck("not_a_unit", None)
    if known is not None:
        return UnitCheck("known", known)
    name = custom_unit_name(word)
    return UnitCheck("new", name) if name else UnitCheck("not_a_unit", None)


def vocabulary_for_person(answer: dict[str, Any], available: Sequence[str]) -> dict[str, Any]:
    """The shared answer with the caller's units (spec 055). Never cached across people."""
    return {**answer, "units": list(available)}


def vocabulary_answer(*, max_text_chars: int) -> dict[str, Any]:
    return {
        "units": list(ALLOWED_UNITS),
        "sizes": list(SIZES),
        "max_text_chars": max_text_chars,
    }
