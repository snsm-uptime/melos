"""Ingredient catalog matching (spec 018, research §3 and §4): name normalization and the rule.

Pure: no I/O and no SDK imports (constitution §3). The model proposes a catalog entry for each
line; `match_line` confirms the proposal only when the line's name is the same name under the
normalization below, and rejects it otherwise.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Literal, get_args

from domain.errors import (
    CatalogNameBlankError,
    CatalogNameChangedError,
    CatalogNameExistsError,
    CatalogNameOwnOtherError,
    CatalogNameUnknownError,
    SameIngredientError,
)

_SPACES = re.compile(r"\s+")
_VOWELS = frozenset("aeiou")

# English plurals whose singular ends in "f" or "fe" do not follow the "-s" rule.
_VES_TO_SINGULAR = {
    "leaves": "leaf",
    "loaves": "loaf",
    "halves": "half",
    "calves": "calf",
    "shelves": "shelf",
    "wolves": "wolf",
    "knives": "knife",
}


@dataclass(frozen=True)
class LineMatch:
    """The label on a draft line (FR-001). `entry` is set exactly when `kind` is "matched"."""

    kind: Literal["matched", "new"]
    entry: str | None = None


@dataclass(frozen=True)
class NameChange:
    """A listed change from the text's name to the catalog entry it matches (FR-003)."""

    line: int
    from_name: str
    to: str


NEW = LineMatch(kind="new")

Language = Literal["en", "es"]
LANGUAGES: tuple[Language, ...] = get_args(Language)


def as_language(value: str | None) -> Language | None:
    """The value when it is a supported language, else None."""
    return value if value in LANGUAGES else None  # type: ignore[return-value]


@dataclass(frozen=True)
class CatalogEntry:
    """One catalog ingredient: its kept name and its other names (spec 043).

    `language` is the kept name's language, or None when nobody has set it. `variants` holds at
    most one name per other language; `spellings` are same-language names, only for matching.
    """

    name: str
    language: Language | None = None
    variants: Mapping[Language, str] = field(default_factory=dict)
    spellings: tuple[str, ...] = ()

    def other_names(self) -> tuple[str, ...]:
        return (*self.variants.values(), *self.spellings)

    def all_names(self) -> tuple[str, ...]:
        return (self.name, *self.other_names())


def _spelling_key(name: str) -> str:
    return _SPACES.sub(" ", name.casefold()).strip()


class CatalogIndex:
    """Every name of one notebook's catalog, each pointing at its kept name (research R4).

    Built from kept names alone it gives exactly the S-018 answers; other names add to them.
    """

    def __init__(self, entries: Iterable[CatalogEntry]) -> None:
        self._entries: dict[str, CatalogEntry] = {}
        self._exact: dict[str, str] = {}
        self._spelling: dict[str, str] = {}
        self._keys: dict[str, list[str]] = {}
        self._forms: dict[str, list[str]] = {}
        for entry in entries:
            if not entry.name or entry.name in self._entries:
                continue
            self._entries[entry.name] = entry
            for name in entry.all_names():
                self._exact.setdefault(name, entry.name)
                self._spelling.setdefault(_spelling_key(name), entry.name)
                key = normalize_name(name)
                _add_once(self._keys, key, entry.name)
                for form in singular_forms(key):
                    _add_once(self._forms, form, entry.name)

    @classmethod
    def build(cls, entries: Iterable[CatalogEntry]) -> CatalogIndex:
        return cls(entries)

    @classmethod
    def of_names(cls, names: Iterable[str]) -> CatalogIndex:
        """An index of kept names with no other names: the catalog before spec 043."""
        return cls(CatalogEntry(name=n) for n in names if n and n.strip())

    def kept_names(self) -> list[str]:
        return list(self._entries)

    def all_names(self) -> list[str]:
        """Kept and other names, sorted, so the first match is the same in any order."""
        return sorted(self._exact)

    def entry(self, kept: str) -> CatalogEntry | None:
        return self._entries.get(kept)

    def kept_of(self, name: str) -> str | None:
        """The kept name when `name` is exactly one of the catalog's names."""
        return self._exact.get(name)

    def kept_for_spelling(self, name: str) -> str | None:
        """The kept name when `name` differs from a catalog name only by case or spaces."""
        return self._spelling.get(_spelling_key(name))

    def matches(self, name: str) -> list[str]:
        """Every kept name the S-018 rule matches `name` to, through any of its names.

        In a fixed order: the same name first, then names it is a plural of, then names whose
        plural it is (each sorted), so the answer never depends on set order.
        """
        key = normalize_name(name)
        if not key:
            return []
        found: list[str] = []
        for kept in self._keys.get(key, []):
            _append_once(found, kept)
        for form in sorted(singular_forms(key)):
            for kept in self._keys.get(form, []):
                _append_once(found, kept)
        for kept in self._forms.get(key, []):
            _append_once(found, kept)
        return found

    def kept_for(self, name: str) -> str | None:
        """The first kept name `matches` gives, or None."""
        found = self.matches(name)
        return found[0] if found else None

    def has_other_names(self) -> bool:
        return any(e.other_names() for e in self._entries.values())


CatalogLike = CatalogIndex | Iterable[str]


def _add_once(table: dict[str, list[str]], key: str, kept: str) -> None:
    _append_once(table.setdefault(key, []), kept)


def _append_once(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def as_index(catalog: CatalogLike) -> CatalogIndex:
    """Accept an index, or plain kept names as the callers before spec 043 pass them."""
    return catalog if isinstance(catalog, CatalogIndex) else CatalogIndex.of_names(catalog)


def shown_name(entry: CatalogEntry, language: str | None) -> str:
    """The name a line shows in `language`: the variant in it, else the kept name (FR-006)."""
    if language is None or entry.language == language:
        return entry.name
    return entry.variants.get(language, entry.name)  # type: ignore[call-overload]


def shown_for(index: CatalogIndex, kept: str, language: str | None) -> str:
    entry = index.entry(kept)
    return kept if entry is None else shown_name(entry, language)


def name_taken(index: CatalogIndex, name: str) -> bool:
    """Whether the name is already a kept or other name of the catalog, by spelling."""
    return index.kept_for_spelling(name) is not None


def normalize_name(text: str) -> str:
    """Trim, drop accents, casefold and collapse spaces. Two names are the same when these match."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _SPACES.sub(" ", without_accents.casefold()).strip()


def same_spelling(first: str, second: str) -> bool:
    """True when two names differ only in letter case or spaces, so no change is listed (FR-003)."""
    return _SPACES.sub(" ", first.casefold()).strip() == _SPACES.sub(" ", second.casefold()).strip()


def singular_forms(normalized: str) -> frozenset[str]:
    """The name and every singular it may be, from fixed English and Spanish rules."""
    forms = {normalized}
    word = normalized
    head, _, last = word.rpartition(" ")
    if last in _VES_TO_SINGULAR:
        forms.add(f"{head} {_VES_TO_SINGULAR[last]}".strip())
    if len(word) > 4 and word.endswith("ies"):
        forms.add(word[:-3] + "y")
    if len(word) > 4 and word.endswith("oes"):
        forms.add(word[:-2])
    if len(word) > 4 and word.endswith("es") and word[-3] not in _VOWELS:
        forms.add(word[:-2])
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        forms.add(word[:-1])
    return frozenset(forms)


def _same_name(first: str, second: str) -> bool:
    first_key, second_key = normalize_name(first), normalize_name(second)
    return second_key in singular_forms(first_key) or first_key in singular_forms(second_key)


def match_line(
    text_name: str | None,
    name: str,
    proposal: str | None,
    catalog: CatalogLike,
) -> LineMatch:
    """Confirm the model's proposal for one line, or reject it (research §3).

    A line matches only when the proposal is a name of the catalog and the line's name is the
    same name as it, singular forms included. The match is the proposal's kept name, so a line
    that names an other name ("cebollas" for "cebolla") matches its ingredient (spec 043 FR-008).
    A line with no proposal is new.
    """
    index = as_index(catalog)
    kept = index.kept_of(proposal) if proposal is not None else None
    if proposal is None or kept is None:
        return NEW
    if _same_name(text_name or name, proposal):
        return LineMatch(kind="matched", entry=kept)
    return NEW


def propose_entry(name: str, catalog: CatalogLike) -> str | None:
    """The kept name of the first catalog name the name matches under `match_line`, or None.

    Used when a member types a name in an edit (spec 027 FR-009): no model is involved, so the
    proposal is the same fixed rule that confirms the model's proposals at capture.
    """
    if not name.strip():
        return None
    index = as_index(catalog)
    for candidate in index.all_names():
        match = match_line(None, name, candidate, index)
        if match.kind == "matched":
            return match.entry
    return None


def names_to_add(incoming: Iterable[str], existing: CatalogLike) -> list[str]:
    """The incoming names no known name matches, when someone joins a notebook (spec 057).

    The rule is `match_line`'s: two names match when one's key is among the other's singular
    forms. Two sets give that answer in linear time, where `propose_entry` per name would be
    quadratic or worse (research R6). Sorted input makes the result the same for any order, and
    each accepted name becomes known, so "tomato" and "tomatoes" add one name (FR-018). An
    index's other names count as known (spec 043).
    """
    known = existing.all_names() if isinstance(existing, CatalogIndex) else existing
    keys: set[str] = set()
    forms: set[str] = set()
    for name in known:
        key = normalize_name(name)
        keys.add(key)
        forms |= singular_forms(key)

    added: list[str] = []
    for name in sorted(incoming):
        key = normalize_name(name)
        name_forms = singular_forms(key)
        if not key or key in forms or name_forms & keys:
            continue
        added.append(name)
        keys.add(key)
        forms |= name_forms
    return added


# --- catalog management (spec 043) ------------------------------------------------------------

OtherNameKind = Literal["variant", "spelling"]


@dataclass(frozen=True)
class OtherName:
    """One other name to store under an ingredient: a variant needs a language, a spelling none."""

    name: str
    kind: OtherNameKind
    language: Language | None = None


@dataclass(frozen=True)
class MergePlan:
    """What one notebook's merge writes (data-model "State transitions")."""

    merged: str
    kept: str
    kept_language: Language | None
    other_names: tuple[OtherName, ...]


def plan_merge(
    index: CatalogIndex,
    merged: str,
    kept: str,
    merged_language: str | None,
    kept_language: str | None,
) -> MergePlan:
    """Merge one ingredient into another in one notebook's catalog (FR-005, edge cases).

    Each name resolves by the S-018 rule, so "onions" finds "onion". The kept entry keeps its
    language, or takes `kept_language` when it has none. The merged name, then each of the
    merged entry's own other names, becomes a variant when its language differs from the kept
    language and the kept entry has no variant in it yet; otherwise a spelling.
    """
    merged_kept = index.kept_for(merged)
    kept_kept = index.kept_for(kept)
    if merged_kept is None or kept_kept is None:
        raise CatalogNameUnknownError()
    if merged_kept == kept_kept:
        raise SameIngredientError()
    kept_entry = index.entry(kept_kept)
    merged_entry = index.entry(merged_kept)
    assert kept_entry is not None and merged_entry is not None

    language = kept_entry.language or as_language(kept_language)
    taken: set[str] = set(kept_entry.variants)
    if language is not None:
        taken.add(language)
    others: list[OtherName] = []

    def place(name: str, name_language: Language | None) -> None:
        if name_language is not None and name_language not in taken:
            taken.add(name_language)
            others.append(OtherName(name, "variant", name_language))
        else:
            others.append(OtherName(name, "spelling"))

    place(merged_entry.name, as_language(merged_language) or merged_entry.language)
    for variant_language, name in merged_entry.variants.items():
        place(name, variant_language)
    for name in merged_entry.spellings:
        place(name, None)
    return MergePlan(
        merged=merged_kept,
        kept=kept_kept,
        kept_language=language,
        other_names=tuple(others),
    )


def normalize_new_name(text: str) -> str:
    """Trim, lower-case and collapse spaces; the singular when the S-018 rules give just one."""
    name = _SPACES.sub(" ", text.strip().lower())
    shorter = [form for form in singular_forms(name) if len(form) < len(name)]
    return shorter[0] if len(shorter) == 1 else name


def check_rename(index: CatalogIndex, old: str, new: str) -> str | None:
    """The stored form of the new name, or None when nothing would change (FR-010, FR-011).

    Raises CatalogNameChangedError when `old` is no longer a kept name, CatalogNameBlankError
    for a blank name, and CatalogNameExistsError(existing) when the new name is already a name
    of the catalog, or the same name as one under the S-018 rules.
    """
    if index.entry(old) is None:
        raise CatalogNameChangedError()
    name = normalize_new_name(new)
    if not name:
        raise CatalogNameBlankError()
    if same_spelling(name, old):
        return None
    spelled = index.kept_for_spelling(name)
    if spelled == old:
        # One of its own other names: merging into itself makes no sense (T063).
        raise CatalogNameOwnOtherError()
    if spelled is not None:
        raise CatalogNameExistsError(spelled)
    # Another ingredient with the same name under the S-018 rules; the old name itself is fine
    # ("tomatoe" may become "tomato" even though they share a plural).
    existing = next((kept for kept in index.matches(name) if kept != old), None)
    if existing is not None:
        raise CatalogNameExistsError(existing)
    return name


@dataclass(frozen=True)
class SplitPlan:
    """An other name made its own ingredient again (FR-014, User Story 4).

    For a variant, the lines of recipes in `move_language` move to the split name, so each
    still shows the same word. A spelling never shows, so no line moves.
    """

    name: str
    language: Language | None
    move_language: Language | None


def split_plan(entry: CatalogEntry, other_name: str) -> SplitPlan:
    for language, name in entry.variants.items():
        if same_spelling(name, other_name):
            return SplitPlan(name=name, language=language, move_language=language)
    for name in entry.spellings:
        if same_spelling(name, other_name):
            return SplitPlan(name=name, language=None, move_language=None)
    raise CatalogNameChangedError()


def sorted_pair(first: str, second: str) -> tuple[str, str]:
    return (first, second) if first < second else (second, first)


def filter_pairs(
    index: CatalogIndex,
    dismissed: Iterable[tuple[str, str]],
    proposed: Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    """The model's (en, es) pairs a person may see (FR-009b).

    Both names must be kept names of the catalog (the model may not invent one), of different
    ingredients, and not dismissed in this notebook. Each pair is listed once, as spelled in
    the catalog.
    """
    gone = {sorted_pair(*pair) for pair in dismissed}
    kept_names = set(index.kept_names())
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str]] = []
    for english, spanish in proposed:
        en = index.kept_for_spelling(english)
        es = index.kept_for_spelling(spanish)
        if en is None or es is None or en == es:
            continue
        if not (same_spelling(en, english) and same_spelling(es, spanish)):
            continue  # an other name stands for an ingredient already merged
        if en not in kept_names or es not in kept_names:
            continue
        key = sorted_pair(en, es)
        if key in gone or key in seen:
            continue
        seen.add(key)
        pairs.append((en, es))
    return pairs
