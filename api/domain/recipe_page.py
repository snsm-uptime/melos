"""Recipes read from a web page (spec 026, research R6 to R8).

- `recipes_from_jsonld` maps schema.org Recipe items, already parsed from the page's
  `<script type="application/ld+json">` blocks, to `PageRecipe` values.
- `markdown_from` and `apply_page_recipe` build the schema.org path (AC2.3): the ingredient
  lines go through the extractor, the title, steps and servings come from the data.
- `split_markdown` cuts a long page into batches on block boundaries, and `merge_parts` joins
  the parts the extractor returns in partial page mode into one raw draft (SC-009).

Pure: values in, values out, no I/O.
"""

from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, replace

from domain.recipe_draft import MAX_TITLE_CHARS, DraftRecipe, IngredientLine


@dataclass(frozen=True, slots=True)
class PageRecipe:
    """One schema.org Recipe item, as plain text."""

    title: str | None
    yield_text: str | None
    ingredients: tuple[str, ...]
    steps: tuple[str, ...]
    image_urls: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DraftPart:
    """What one part of a page holds (partial page mode). Never checked alone."""

    title: str | None
    base_servings: int | None
    ingredient_lines: tuple[IngredientLine, ...]
    steps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NoRecipeContent:
    """A part, or a whole page, with no title, ingredient line or step in it."""


@dataclass(frozen=True, slots=True)
class MultipleRecipes:
    """The page holds two or more recipes."""


@dataclass(frozen=True, slots=True)
class PageBatches:
    batches: tuple[str, ...]
    # True when Markdown beyond the batch cap was dropped (the draft shows the long-page note).
    cut: bool


# --- schema.org JSON-LD ---

_TAG = re.compile(r"<[^>]*>")
_BREAK = re.compile(r"<\s*br\s*/?\s*>|<\s*/\s*(p|li|div)\s*>", re.I)
_SPACES = re.compile(r"\s+")
# A removed tag leaves a space: "until <b>soft</b>." must read "until soft."
_SPACE_BEFORE_MARK = re.compile(r"\s+([.,;:!?)])")


def _text(value: object) -> str:
    """Plain text: entities decoded, tags removed, spaces folded."""
    if not isinstance(value, str):
        return ""
    folded = _SPACES.sub(" ", _TAG.sub(" ", html.unescape(value)))
    return _SPACE_BEFORE_MARK.sub(r"\1", folded).strip()


def _lines(value: str) -> list[str]:
    with_breaks = _BREAK.sub("\n", html.unescape(value))
    return [text for text in (_text(line) for line in with_breaks.splitlines()) if text]


def _is_recipe(node: dict) -> bool:
    kind = node.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    return any(isinstance(item, str) and re.split(r"[/:]", item)[-1] == "Recipe" for item in kinds)


def _walk(value: object, depth: int = 0) -> Iterator[dict]:
    if depth > 8:
        return
    if isinstance(value, list):
        for item in value:
            yield from _walk(item, depth + 1)
        return
    if not isinstance(value, dict):
        return
    if _is_recipe(value):
        yield value
        return
    for key in ("@graph", "mainEntity"):
        if key in value:
            yield from _walk(value[key], depth + 1)


def _steps(value: object, depth: int = 0) -> list[str]:
    if depth > 6:
        return []
    if isinstance(value, str):
        return _lines(value)
    if isinstance(value, list):
        return [step for item in value for step in _steps(item, depth + 1)]
    if isinstance(value, dict):
        if "itemListElement" in value:  # HowToSection or ItemList: flattened in order (FR-015)
            return _steps(value["itemListElement"], depth + 1)
        text = _text(value.get("text")) or _text(value.get("name"))
        return [text] if text else []
    return []


def _ingredients(value: object) -> list[str]:
    if isinstance(value, str):
        return _lines(value)
    if isinstance(value, list):
        return [text for text in (_text(item) for item in value) if text]
    return []


def _images(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [url for item in value for url in _images(item)]
    if isinstance(value, dict):
        return _images(value.get("url") or value.get("contentUrl"))
    return []


def _yield_text(value: object) -> str | None:
    if isinstance(value, list):
        value = next((item for item in value if isinstance(item, (str, int))), None)
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return str(int(value))
    text = _text(value)
    return text or None


def recipes_from_jsonld(objects: Iterable[object]) -> tuple[PageRecipe, ...]:
    """Every schema.org Recipe item found in plain objects, lists, `@graph` and `mainEntity`."""
    recipes: list[PageRecipe] = []
    for value in objects:
        for node in _walk(value):
            recipes.append(
                PageRecipe(
                    title=_text(node.get("name")) or None,
                    yield_text=_yield_text(node.get("recipeYield")),
                    ingredients=tuple(
                        _ingredients(node.get("recipeIngredient", node.get("ingredients")))
                    ),
                    steps=tuple(_steps(node.get("recipeInstructions"))),
                    image_urls=tuple(_images(node.get("image"))),
                )
            )
    return tuple(recipes)


_FIRST_NUMBER = re.compile(r"\d+")


def parse_yield(text: str | int | None) -> int | None:
    """The first whole number of the yield ("Serves 4-6" is 4), or None when there is none."""
    if text is None or isinstance(text, bool):
        return None
    match = _FIRST_NUMBER.search(str(text))
    if match is None:
        return None
    value = int(match.group())
    return value if value >= 1 else None


def markdown_from(recipe: PageRecipe) -> str:
    """A short text of the schema.org recipe, for the extractor's ingredient rules."""
    sections: list[str] = []
    if recipe.title:
        sections.append(f"# {recipe.title}")
    if recipe.yield_text:
        sections.append(f"Servings: {recipe.yield_text}")
    if recipe.ingredients:
        items = "\n".join(f"- {line}" for line in recipe.ingredients)
        sections.append(f"## Ingredients\n\n{items}")
    if recipe.steps:
        items = "\n".join(f"{index}. {step}" for index, step in enumerate(recipe.steps, 1))
        sections.append(f"## Steps\n\n{items}")
    return "\n\n".join(sections)


def apply_page_recipe(draft: DraftRecipe, recipe: PageRecipe) -> DraftRecipe:
    """The page's title, steps and whole-number servings win over the model's (AC2.3)."""
    title = draft.title
    if recipe.title:
        title = recipe.title[:MAX_TITLE_CHARS].strip()
    steps = recipe.steps or draft.steps
    servings = parse_yield(recipe.yield_text)
    if servings is None:
        return replace(draft, title=title, steps=steps)
    return replace(
        draft, title=title, steps=steps, base_servings=servings, servings_estimated=False
    )


# --- batches ---


def _cut_line(line: str, limit: int) -> list[str]:
    """A single line longer than a batch, cut at spaces (or hard, for one huge word)."""
    pieces: list[str] = []
    rest = line
    while len(rest) > limit:
        cut = rest.rfind(" ", 0, limit + 1)
        if cut <= 0:
            pieces.append(rest[:limit])
            rest = rest[limit:]
        else:
            pieces.append(rest[:cut])
            rest = rest[cut + 1 :]
    if rest:
        pieces.append(rest)
    return pieces


def _units(markdown: str, limit: int) -> Iterator[tuple[str, str]]:
    """(text, joiner) in page order: blocks, or the lines of an over-long block."""
    for block in re.split(r"\n[ \t]*\n", markdown):
        block = block.strip("\n")
        if not block.strip():
            continue
        if len(block) <= limit:
            yield block, "\n\n"
            continue
        line_joiner = "\n\n"
        for line in block.split("\n"):
            pieces = _cut_line(line, limit) if len(line) > limit else [line]
            yield pieces[0], line_joiner
            for piece in pieces[1:]:
                yield piece, " "
            line_joiner = "\n"


def split_markdown(markdown: str, batch_chars: int, max_batches: int) -> PageBatches:
    """Batches of at most `batch_chars`, cut only on blank lines, then line breaks."""
    batches: list[str] = []
    current = ""
    for text, joiner in _units(markdown.strip(), batch_chars):
        if not current:
            current = text
        elif len(current) + len(joiner) + len(text) <= batch_chars:
            current = current + joiner + text
        else:
            batches.append(current)
            current = text
    if current:
        batches.append(current)
    if len(batches) > max_batches:
        return PageBatches(batches=tuple(batches[:max_batches]), cut=True)
    return PageBatches(batches=tuple(batches), cut=False)


# --- merging (SC-009) ---


def _fold(text: str | None) -> str:
    return (text or "").strip().lower()


def _line_key(line: IngredientLine) -> tuple[object, ...]:
    return (
        _fold(line.name),
        line.vague,
        line.quantity,
        _fold(line.unit),
        _fold(line.size),
        _fold(line.preparation),
        _fold(line.vague_text),
        _fold(line.note),
    )


def _step_key(step: str) -> str:
    return _SPACES.sub(" ", step).strip()


def _title_key(title: str) -> str:
    decomposed = unicodedata.normalize("NFKD", title.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch) and not ch.isspace())


def _same_title(a: str, b: str) -> bool:
    """Equal after folding case, accents and spaces, or one inside the other: a printable
    card titled "Bean stew (printable card)" repeats "Bean stew", it is not a second recipe."""
    first, second = _title_key(a), _title_key(b)
    return first == second or first in second or second in first


def merge_parts(
    parts: Sequence[DraftPart | NoRecipeContent | MultipleRecipes],
) -> DraftRecipe | MultipleRecipes | NoRecipeContent:
    """One raw draft from the parts in batch order, for `check_draft`; or a refusal."""
    if any(isinstance(part, MultipleRecipes) for part in parts):
        return MultipleRecipes()
    found = [part for part in parts if isinstance(part, DraftPart)]
    if not found:
        return NoRecipeContent()

    complete = [part.title for part in found if part.title and part.ingredient_lines and part.steps]
    if any(not _same_title(complete[0], other) for other in complete[1:]):
        return MultipleRecipes()

    title = next((part.title for part in found if part.title), None)
    servings = next((part.base_servings for part in found if part.base_servings), None)
    lines: list[IngredientLine] = []
    line_keys: set[tuple[object, ...]] = set()
    steps: list[str] = []
    step_keys: set[str] = set()
    for part in found:
        for line in part.ingredient_lines:
            key = _line_key(line)
            if key not in line_keys:
                line_keys.add(key)
                lines.append(line)
        for step in part.steps:
            key = _step_key(step)
            if key and key not in step_keys:
                step_keys.add(key)
                steps.append(step)
    return DraftRecipe(
        title=title or "",
        base_servings=servings,
        servings_estimated=False,
        ingredient_lines=tuple(lines),
        steps=tuple(steps),
    )
