"""The text a recipe is embedded from (spec 019 FR-022, research R8).

Two named strategies, chosen by EMBED_TEXT_STRATEGY:

- `toon` (default): the PRD Appendix B.3 shape the assistant reads, without the `id` field,
  encoded with `python-toon` (PRD Appendix D).
- `plain`: title, servings, one line per ingredient, then the steps.

Both put the title and the ingredients before the steps, so a recipe the service cuts at its
input limit keeps what matters most (research R2a).

Pure: imports only the `toon` encoder and the standard library.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol

from toon import encode


class EmbedLine(Protocol):
    name: str
    vague: bool
    quantity: float | None
    unit: str | None
    size: str | None
    preparation: str | None
    note: str | None


class EmbedRecipe(Protocol):
    """What a strategy reads: a stored recipe's content (application.ports.RecipeDetail)."""

    title: str
    base_servings: int
    lines: Sequence[EmbedLine]
    steps: Sequence[str]


def _number(value: float | None) -> int | float | None:
    if value is None:
        return None
    return int(value) if float(value).is_integer() else float(value)


def toon(recipe: EmbedRecipe) -> str:
    document: dict[str, Any] = {
        "title": recipe.title,
        "base_servings": recipe.base_servings,
        "ingredients": [
            {
                "name": line.name,
                "quantity": _number(line.quantity),
                "unit": line.unit,
                "size": line.size,
                "preparation": line.preparation,
                "vague_note": line.note,
            }
            for line in recipe.lines
        ],
        "steps": list(recipe.steps),
    }
    return encode(document)


def _plain_line(line: EmbedLine) -> str:
    parts = [
        str(part)
        for part in (_number(line.quantity), line.unit, line.size, line.name)
        if part is not None and part != ""
    ]
    text = " ".join(parts)
    if line.preparation:
        text = f"{text}, {line.preparation}"
    if line.note:
        text = f"{text} ({line.note})"
    return f"- {text}"


def plain(recipe: EmbedRecipe) -> str:
    lines = [recipe.title, f"Serves {recipe.base_servings}.", "Ingredients:"]
    lines.extend(_plain_line(line) for line in recipe.lines)
    if recipe.steps:
        lines.append("Steps:")
        lines.extend(f"{number}. {step}" for number, step in enumerate(recipe.steps, start=1))
    return "\n".join(lines)


STRATEGIES: dict[str, Callable[[EmbedRecipe], str]] = {"toon": toon, "plain": plain}
