"""The controlled lists the draft editor shows (spec 016 FR-011, FR-012; GET /recipe-vocabulary).

Pure: it shapes the parsed `categories.yaml` and `cuisine.yml` contents and does no I/O.
Only assignable cuisines are listed: tag and variant nodes, plus the fallback. A variant
carries its nearest tag on the primary parent chain, as `score_cuisines` does.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from domain.recipe_draft import ALLOWED_UNITS, MAX_CUISINES, MAX_MAIN_INGREDIENTS, SIZES


def _tag_of(cuisines: Mapping[str, Any], cuisine_id: str) -> str:
    """The nearest tag on the primary parent chain, the node itself when it is a tag."""
    current_id = cuisine_id
    current = cuisines[current_id]
    while current.get("role") != "tag" and current.get("parents"):
        current_id = current["parents"][0]
        current = cuisines[current_id]
    return current_id


def vocabulary_answer(
    categories: Mapping[str, Any],
    cuisine: Mapping[str, Any],
    *,
    max_text_chars: int,
) -> dict[str, Any]:
    main_values = categories["categories"]["main_ingredient"]["values"]
    cuisines = cuisine["cuisines"]

    listed: list[dict[str, Any]] = []
    for cuisine_id, node in cuisines.items():
        if node.get("kind") == "fallback":
            listed.append({"id": cuisine_id, "label": node["label"], "tag": None})
        elif node.get("role") == "tag":
            listed.append({"id": cuisine_id, "label": node["label"], "tag": None})
        elif node.get("role") == "variant":
            tag = _tag_of(cuisines, cuisine_id)
            listed.append({"id": cuisine_id, "label": node["label"], "tag": tag})

    return {
        "units": list(ALLOWED_UNITS),
        "sizes": list(SIZES),
        "max_main_ingredients": MAX_MAIN_INGREDIENTS,
        "max_cuisines": MAX_CUISINES,
        "max_text_chars": max_text_chars,
        "main_ingredients": [
            {"id": key, "label": value["label"]} for key, value in main_values.items()
        ],
        "cuisines": listed,
    }
