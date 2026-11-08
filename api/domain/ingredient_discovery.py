"""Pure rule for finding new standard ingredients in recipe lines (spec 073, US1).

The persistence adapter selects the recipe lines since the watermark; this module turns them into
distinct candidates keyed by `discovery_key`. No I/O.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from domain.ingredient_catalog import discovery_key
from domain.ingredient_translation import MAX_TRANSLATION_LENGTH, Language

# The standard name limit is the same as a translation's (data-model: at most 80 characters).
MAX_NAME_LENGTH = MAX_TRANSLATION_LENGTH


@dataclass(frozen=True, slots=True)
class RecipeLineName:
    """One recipe line's ingredient name, with the language of the recipe it belongs to."""

    name: str
    recipe_language: str | None


@dataclass(frozen=True, slots=True)
class Candidate:
    """A distinct ingredient found in recipe lines: its key, the first name seen, its language."""

    key: str
    name: str
    language: Language


def discover(lines: Iterable[RecipeLineName]) -> list[Candidate]:
    """Distinct candidates in first-seen order. A line with no name or no supported language is
    skipped: the standard table needs a language to translate from (spec 073, T027)."""
    found: dict[str, Candidate] = {}
    for line in lines:
        name = line.name.strip()
        language = _supported(line.recipe_language)
        if not name or language is None or len(name) > MAX_NAME_LENGTH or "\n" in name:
            continue
        key = discovery_key(name)
        if not key or key in found:
            continue
        found[key] = Candidate(key=key, name=name, language=language)
    return list(found.values())


def _supported(value: str | None) -> Language | None:
    if value == "en":
        return "en"
    if value == "es":
        return "es"
    return None
