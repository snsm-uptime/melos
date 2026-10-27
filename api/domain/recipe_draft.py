"""Recipe draft rules for pasted-text extraction (spec FR-006 to FR-006c).

Pure rules: no I/O, SDK, FastAPI or database imports. The controlled vocabulary
(categories.yaml and cuisine.yml) is read by an adapter and passed in as parsed
data through `build_vocabulary`.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from functools import cache, lru_cache
from typing import Any

from domain.errors import DomainError
from domain.ingredient_catalog import LineMatch, NameChange, match_line, same_spelling

ALLOWED_UNITS = ("g", "kg", "oz", "lb", "ml", "l", "cup", "tbsp", "tsp", "unit")
SIZES = ("small", "medium", "large")
DEFAULT_SERVINGS = 4
MAX_TITLE_CHARS = 200
MAX_MAIN_INGREDIENTS = 2
MAX_CUISINES = 2
INTERNATIONAL = "international"

# Spellings from the FR-006a table, English and Spanish. Keys are allowed units.
UNIT_SPELLINGS: dict[str, tuple[str, ...]] = {
    "g": ("gram", "grams", "g", "gr", "gramo", "gramos"),
    "kg": ("kilogram", "kilograms", "kg", "kilo", "kilos", "kilogramo", "kilogramos"),
    "oz": ("ounce", "ounces", "oz", "onza", "onzas"),
    "lb": ("pound", "pounds", "lb", "lbs", "libra", "libras"),
    "ml": ("milliliter", "milliliters", "ml", "mililitro", "mililitros"),
    "l": ("liter", "liters", "l", "litro", "litros"),
    "cup": ("cup", "cups", "taza", "tazas"),
    "tbsp": (
        "tablespoon",
        "tablespoons",
        "tbsp",
        "tbs",
        "tbl",
        "cucharada",
        "cucharadas",
        "cda",
        "cdas",
    ),
    "tsp": (
        "teaspoon",
        "teaspoons",
        "tsp",
        "cucharadita",
        "cucharaditas",
        "cdta",
        "cdtas",
    ),
    "unit": (
        "piece",
        "pieces",
        "whole",
        "each",
        "pieza",
        "caja",
        "box",
        "piezas",
        "unidad",
        "unidades",
        "entero",
        "enteros",
        "clove",
        "diente",
        "dientes",
        "diente de ajo",
        "dientes de ajo",
    ),
}


class InvalidDraftError(DomainError):
    """Raised when a draft breaks a recipe rule. The whole draft is then invalid output."""

    MESSAGE = "The recipe breaks a recipe rule."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.MESSAGE)


class LineProblemKind(StrEnum):
    QUANTITY_MISSING = "quantity_missing"
    UNIT_MISSING = "unit_missing"
    UNIT_NOT_RECOGNIZED = "unit_not_recognized"


@dataclass(frozen=True, slots=True)
class LineProblem:
    name: str
    kind: LineProblemKind


class DraftProblems(DomainError):
    """A draft the user can fix: missing title or steps, or unusable line quantity or unit."""

    def __init__(
        self,
        missing: tuple[str, ...] = (),
        line_problems: tuple[LineProblem, ...] = (),
    ) -> None:
        super().__init__("The recipe draft is incomplete.")
        self.missing = missing
        self.line_problems = line_problems


@dataclass(frozen=True, slots=True)
class IngredientLine:
    name: str
    vague: bool
    quantity: float | None = None
    unit: str | None = None
    size: str | None = None
    note: str | None = None
    # How the ingredient is cut or prepared ("chopped"). Never part of name (FR-010).
    preparation: str | None = None
    # The name as written in the pasted text, and the catalog entry the model proposes (spec 018).
    text_name: str | None = None
    catalog_match: str | None = None


@dataclass(frozen=True, slots=True)
class DraftRecipe:
    """A draft as the adapter reads it (raw) and as the domain returns it (checked).

    `base_servings` is None when the text gives none; `check_draft` fills in the
    default and sets the estimate flag. `cuisines` is empty in the raw value:
    the app scores cuisines, not the model. `matches` has one entry per ingredient line
    and `changes` lists the name changes the member sees (spec 018); both are empty
    in the raw value.
    """

    title: str
    base_servings: int | None
    servings_estimated: bool
    main_ingredients: tuple[str, ...]
    cuisines: tuple[str, ...]
    ingredient_lines: tuple[IngredientLine, ...]
    steps: tuple[str, ...]
    matches: tuple[LineMatch, ...] = ()
    changes: tuple[NameChange, ...] = ()


# ── units ───────────────────────────────────────────────────────────────────


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _unit_key(raw: str) -> str:
    key = _strip_accents(raw).lower().strip()
    if key.endswith("."):
        key = key[:-1]
    return key.strip()


@cache
def _unit_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for unit, spellings in UNIT_SPELLINGS.items():
        index[unit] = unit
        for spelling in spellings:
            index[_strip_accents(spelling).lower()] = unit
    return index


def _within_one_edit(a: str, b: str) -> bool:
    """True when `a` and `b` differ by exactly one added, removed or changed letter."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b, strict=True)) == 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    i = 0
    while i < len(short) and short[i] == long_[i]:
        i += 1
    return short[i:] == long_[i + 1 :]


def lookup_unit(raw: str) -> str | None:
    """Map a service unit to its allowed unit, or None when it is unknown (FR-006a).

    A unit one edit away from a table spelling is matched when it is 5 or more
    characters long. One edit away from the spellings of more than one allowed
    unit is invalid output.
    """
    key = _unit_key(raw)
    if not key:
        return None
    index = _unit_index()
    if key in index:
        return index[key]
    if len(key) < 5:
        return None
    near = {unit for spelling, unit in index.items() if _within_one_edit(key, spelling)}
    if len(near) > 1:
        raise InvalidDraftError("ambiguous unit")
    return near.pop() if near else None


# ── vocabulary ──────────────────────────────────────────────────────────────


def _normalize(text: str) -> str:
    """Lower-case, accents removed, punctuation and spacing collapsed to single spaces."""
    return " ".join(re.findall(r"[a-z0-9]+", _strip_accents(text).lower()))


@lru_cache(maxsize=4096)
def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![a-z0-9]){re.escape(phrase)}(?:s|es)?(?![a-z0-9])")


def _occurrences(text: str, phrase: str) -> list[tuple[int, int]]:
    """Whole-word matches of `phrase` in normalized `text`, plurals included."""
    if not phrase:
        return []
    return [(m.start(), m.end()) for m in _phrase_pattern(phrase).finditer(text)]


@dataclass(frozen=True, slots=True)
class _Matching:
    stopwords: frozenset[str]
    exclusions: tuple[tuple[str, frozenset[str]], ...]
    ingredient_items: tuple[tuple[str, tuple[str, ...]], ...]
    min_coverage: float
    min_ingredients: int
    min_recipe_ingredients: int


@dataclass(frozen=True, slots=True)
class _CuisineNode:
    id: str
    tag: str
    phrases: tuple[str, ...]
    ingredient_ids: frozenset[str]
    techniques: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Vocabulary:
    """Controlled vocabulary for categories. Built from parsed YAML by `build_vocabulary`."""

    main_ingredient_keys: tuple[str, ...]
    matching: _Matching
    cuisine_nodes: tuple[_CuisineNode, ...]


def _build_matching(categories: Mapping[str, Any]) -> _Matching:
    matching = categories["matching"]

    stopwords = {_normalize(w) for lang in matching["stopwords"].values() for w in lang}
    exclusions = tuple(
        (_normalize(item["phrase"]), frozenset(item["blocks"]))
        for item in matching.get("phrase_exclusions", [])
    )

    alias_to_ids: dict[str, set[str]] = {}
    for ingredient_id, aliases in categories["ingredients"].items():
        for alias in aliases:
            alias_to_ids.setdefault(_normalize(alias), set()).add(ingredient_id)
    for alias, ids in (categories.get("ambiguous_aliases") or {}).items():
        alias_to_ids.setdefault(_normalize(alias), set()).update(ids)
    items = tuple(
        (alias, tuple(sorted(ids)))
        for alias, ids in sorted(alias_to_ids.items())
        if alias
    )

    cuisine_rules = matching["cuisine"]
    return _Matching(
        stopwords=frozenset(stopwords),
        exclusions=exclusions,
        ingredient_items=items,
        min_coverage=float(cuisine_rules["title"]["min_coverage"]),
        min_ingredients=int(cuisine_rules["steps"]["min_ingredients"]),
        min_recipe_ingredients=int(cuisine_rules["steps"]["min_recipe_ingredients"]),
    )


def _build_cuisine_nodes(cuisines: Mapping[str, Any]) -> tuple[_CuisineNode, ...]:
    """Tag and variant nodes that can be assigned to a draft."""
    nodes: list[_CuisineNode] = []
    for cuisine_id, node in cuisines.items():
        if node.get("role") not in ("tag", "variant") or node.get("kind") == "fallback":
            continue
        tag_id = cuisine_id
        current = node
        while current.get("role") != "tag" and current.get("parents"):
            tag_id = current["parents"][0]
            current = cuisines[tag_id]
        labels = node.get("label", {})
        signals = node.get("signals") or {}
        ingredients = signals.get("ingredients") or {}
        phrases = [
            *labels.values(),
            *(node.get("aliases") or []),
            *(signals.get("dishes") or []),
        ]
        nodes.append(
            _CuisineNode(
                id=cuisine_id,
                tag=tag_id,
                phrases=tuple(p for p in (_normalize(x) for x in phrases) if p),
                ingredient_ids=frozenset(
                    ingredients.get("defining", [])
                    + ingredients.get("characteristic", [])
                    + ingredients.get("common", [])
                ),
                techniques=tuple(
                    t
                    for t in (_normalize(x) for x in signals.get("techniques") or [])
                    if t
                ),
            )
        )
    return tuple(nodes)


def build_vocabulary(
    categories: Mapping[str, Any], cuisine: Mapping[str, Any]
) -> Vocabulary:
    """Build the vocabulary from the parsed categories.yaml and cuisine.yml contents."""
    return Vocabulary(
        main_ingredient_keys=tuple(
            categories["categories"]["main_ingredient"]["values"]
        ),
        matching=_build_matching(categories),
        cuisine_nodes=_build_cuisine_nodes(cuisine["cuisines"]),
    )


def _spans(
    text: str,
    items: Iterable[tuple[str, tuple[str, ...]]],
    exclusions: Sequence[tuple[str, frozenset[str]]] = (),
) -> list[tuple[int, int, tuple[str, ...]]]:
    """Accepted, non-overlapping matches. Longest phrase first, so "queso feta" beats "queso"."""
    excluded_spans = [
        (start, end, blocks)
        for phrase, blocks in exclusions
        for start, end in _occurrences(text, phrase)
    ]
    found = [
        (start, end, keys, len(phrase))
        for phrase, keys in items
        for start, end in _occurrences(text, phrase)
    ]
    found.sort(key=lambda f: (-f[3], f[0]))
    accepted: list[tuple[int, int, tuple[str, ...]]] = []
    for start, end, keys, _ in found:
        if any(start < a_end and a_start < end for a_start, a_end, _ in accepted):
            continue
        blocked = any(
            start < x_end and x_start < end and set(keys) & blocks
            for x_start, x_end, blocks in excluded_spans
        )
        if blocked:
            continue
        accepted.append((start, end, keys))
    return accepted


def _title_coverage(
    title: str, phrases: Sequence[str], stopwords: frozenset[str]
) -> tuple[int, float]:
    """(matched title phrases, share of the title's content words they cover)."""
    tokens = [(m.start(), m.end(), m.group()) for m in re.finditer(r"[a-z0-9]+", title)]
    content = [t for t in tokens if t[2] not in stopwords]
    if not content:
        return 0, 0.0
    phrase_items = [(phrase, ("",)) for phrase in phrases]
    spans = _spans(title, phrase_items)
    covered = sum(
        1 for s, e, _ in content if any(a <= s and e <= b for a, b, _ in spans)
    )
    return len(spans), covered / len(content)


def score_cuisines(
    title: str,
    steps: Sequence[str],
    ingredient_line_count: int,
    vocabulary: Vocabulary,
) -> tuple[str, ...]:
    """Pick up to two cuisine tags or variants from cuisine.yml (FR-006).

    A node matches when its names cover at least the title's minimum share of
    content words, or when at least four of its ingredients appear in the steps.
    The steps rule is off below the minimum recipe ingredient count.
    """
    rules = vocabulary.matching
    title_norm = _normalize(title)
    steps_norm = _normalize(" ".join(steps))
    steps_on = ingredient_line_count >= rules.min_recipe_ingredients

    found_ids: set[str] = set()
    if steps_on:
        for _, _, keys in _spans(steps_norm, rules.ingredient_items, rules.exclusions):
            found_ids.update(keys)

    scored: list[tuple[tuple[int, float, int], str, str]] = []
    for node in vocabulary.cuisine_nodes:
        title_matches, coverage = _title_coverage(
            title_norm, node.phrases, rules.stopwords
        )
        step_ids = node.ingredient_ids & found_ids if steps_on else set()
        matched = (
            coverage >= rules.min_coverage or len(step_ids) >= rules.min_ingredients
        )
        if not matched:
            continue
        techniques = (
            sum(1 for t in node.techniques if _occurrences(steps_norm, t))
            if steps_on
            else 0
        )
        body = len(step_ids) + techniques if steps_on else 0
        total = title_matches + len(step_ids)
        scored.append(((total, coverage, body), node.tag, node.id))

    scored.sort(key=lambda s: s[0], reverse=True)
    chosen: list[str] = []
    seen_tags: set[str] = set()
    for _, tag, node_id in scored:
        if tag in seen_tags:
            continue
        seen_tags.add(tag)
        chosen.append(node_id)
        if len(chosen) == MAX_CUISINES:
            break
    return tuple(chosen) if chosen else (INTERNATIONAL,)


# ── display names ───────────────────────────────────────────────────────────

DISPLAY_NAME_MAX_CHARS = 40


def clean_display_name(raw: str | None) -> str | None:
    """Trim and collapse spaces. None when empty, over 40 characters, or with other characters."""
    cleaned = re.sub(" +", " ", unicodedata.normalize("NFC", raw or "").strip())
    if not cleaned or len(cleaned) > DISPLAY_NAME_MAX_CHARS:
        return None
    if not all(ch.isalpha() or ch in " -'" for ch in cleaned):
        return None
    return cleaned


# ── draft rules ─────────────────────────────────────────────────────────────


def _check_title(title: str) -> str:
    cleaned = (title or "").strip()
    if not cleaned or len(cleaned) > MAX_TITLE_CHARS:
        raise InvalidDraftError("title")
    return cleaned


def _check_steps(steps: Sequence[str]) -> tuple[str, ...]:
    cleaned = tuple(s.strip() for s in steps if s and s.strip())
    if not cleaned:
        raise InvalidDraftError("steps")
    return cleaned


def _check_servings(base_servings: int | None) -> tuple[int, bool]:
    if base_servings is None:
        return DEFAULT_SERVINGS, True
    if base_servings < 1:
        raise InvalidDraftError("servings")
    return base_servings, False


def _normalized_name(raw: str) -> str:
    return (raw or "").strip().lower()


def _check_name(raw: str) -> str:
    name = _normalized_name(raw)
    if not name:
        raise InvalidDraftError("name")
    return name


def _check_line(line: IngredientLine) -> IngredientLine:
    name = _check_name(line.name)
    note = line.note.strip() or None if line.note else None
    preparation = line.preparation.strip() or None if line.preparation else None
    if line.vague:
        if line.quantity is not None or line.unit:
            raise InvalidDraftError("vague line")
        return IngredientLine(name=name, vague=True, note=note, preparation=preparation)

    if line.quantity is None or not math.isfinite(line.quantity) or line.quantity <= 0:
        raise InvalidDraftError("quantity")
    unit = lookup_unit(line.unit or "")
    if unit is None:
        raise InvalidDraftError(
            f"{line.name} unit: {line.unit} quantity: {line.quantity}"
        )
    size = _clean_size(line.size) if unit == "unit" else None
    return IngredientLine(
        name=name,
        vague=False,
        quantity=float(line.quantity),
        unit=unit,
        size=size,
        note=note,
        preparation=preparation,
    )


def _missing_parts(title: str, steps: Sequence[str]) -> tuple[str, ...]:
    missing: list[str] = []
    if not (title or "").strip():
        missing.append("title")
    if not any(s and s.strip() for s in steps):
        missing.append("steps")
    return tuple(missing)


def _line_problems(line: IngredientLine) -> tuple[LineProblem, ...]:
    """Named problems with a non-vague line's amount and unit (FR-003).

    A line with an empty name, or a unit that is ambiguous (InvalidDraftError), gives
    no named problem here: `_check_line` refuses it as invalid output instead.
    """
    name = _normalized_name(line.name)
    if line.vague or not name:
        return ()
    problems: list[LineProblem] = []
    if line.quantity is None or not math.isfinite(line.quantity) or line.quantity <= 0:
        problems.append(LineProblem(name, LineProblemKind.QUANTITY_MISSING))
    if not (line.unit or "").strip():
        problems.append(LineProblem(name, LineProblemKind.UNIT_MISSING))
    else:
        try:
            if lookup_unit(line.unit) is None:
                problems.append(LineProblem(name, LineProblemKind.UNIT_NOT_RECOGNIZED))
        except InvalidDraftError:
            pass
    return tuple(problems)


def _clean_size(raw: str | None) -> str | None:
    size = (raw or "").strip().lower()
    return size if size in SIZES else None


def _main_ingredients(values: Iterable[str], vocabulary: Vocabulary) -> tuple[str, ...]:
    allowed = set(vocabulary.main_ingredient_keys)
    kept: list[str] = []
    for value in values:
        key = (value or "").strip().lower()
        if key in allowed and key not in kept:
            kept.append(key)
    return tuple(kept[:MAX_MAIN_INGREDIENTS])


def _match_lines(
    raw_lines: Sequence[IngredientLine],
    checked_lines: Sequence[IngredientLine],
    catalog: Sequence[str],
) -> tuple[tuple[IngredientLine, ...], tuple[LineMatch, ...], tuple[NameChange, ...]]:
    """Confirm each line's catalog proposal (spec 018) and list the name changes.

    A matched line shows the catalog entry as its name. A change is listed only when the
    text's name differs from that entry in more than letter case or spaces.
    """
    lines: list[IngredientLine] = []
    matches: list[LineMatch] = []
    changes: list[NameChange] = []
    for index, (raw, line) in enumerate(zip(raw_lines, checked_lines, strict=True)):
        # The name as the text writes it; the assistant's name when the text gives none.
        written = raw.text_name or line.name
        match = match_line(raw.text_name, line.name, raw.catalog_match, catalog)
        matches.append(match)
        if match.kind == "matched" and match.entry is not None:
            if not same_spelling(written, match.entry):
                changes.append(
                    NameChange(line=index, from_name=written, to=match.entry)
                )
            line = replace(line, name=match.entry)
        lines.append(replace(line, text_name=written, catalog_match=raw.catalog_match))
    return tuple(lines), tuple(matches), tuple(changes)


def check_draft(
    draft: DraftRecipe,
    catalog_names: Iterable[str],
    vocabulary: Vocabulary,
) -> DraftRecipe:
    """Apply the FR-006 to FR-006c rules to a draft from the service.

    Returns the checked draft with its cuisines scored by the app, and with each
    ingredient matched to the catalog (spec 018). Raises DraftProblems when the member
    can fix the draft: a missing title or steps, or a line with no usable quantity or
    unit. Those named problems are all collected in one pass. Any other broken rule
    raises InvalidDraftError, and the whole draft is then invalid output.
    """
    catalog = tuple[str, ...](n.strip() for n in catalog_names if n and n.strip())
    missing = _missing_parts(draft.title, draft.steps)
    line_problems = tuple[LineProblem, ...](
        problem for line in draft.ingredient_lines for problem in _line_problems(line)
    )
    if missing or line_problems:
        raise DraftProblems(missing=missing, line_problems=line_problems)

    title = _check_title(draft.title)
    steps = _check_steps(draft.steps)
    servings, estimated = _check_servings(draft.base_servings)
    checked = tuple(_check_line(line) for line in draft.ingredient_lines)
    lines, matches, changes = _match_lines(draft.ingredient_lines, checked, catalog)
    return DraftRecipe(
        title=title,
        base_servings=servings,
        servings_estimated=estimated,
        main_ingredients=_main_ingredients(draft.main_ingredients, vocabulary),
        cuisines=score_cuisines(title, steps, len(lines), vocabulary),
        ingredient_lines=lines,
        steps=steps,
        matches=matches,
        changes=changes,
    )
